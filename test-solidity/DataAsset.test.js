// =================================================================================
// 파일명:   DataAsset.test.js
// 목적:     NFT 발급 스마트 컨트랙트 단위테스트
// =================================================================================

const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DataAsset", function () {
// 테스트 전 서버 준비
  async function deployFixture() {
    const [owner, signer, other, minter] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("DataAsset");
    const contract = await Factory.deploy(owner.address, signer.address);
    await contract.waitForDeployment();
    const address = await contract.getAddress();
    return { contract, owner, signer, other, minter, address };
  }
  function structHash(dataHash, minterAddress, chainId, contractAddress) {
    return ethers.keccak256(
      ethers.AbiCoder.defaultAbiCoder().encode(
        ["bytes32", "address", "uint256", "address"],
        [dataHash, minterAddress, chainId, contractAddress]
      )
    );
  }


// 1. 올바른 서명을 가진 사용자에게 NFT가 정상 발급되는지 확인
  it("mint: authorized signer 서명 시 민팅 성공", async function () {
    const { contract, signer, minter, address } = await deployFixture();
    const dataHash = ethers.keccak256(ethers.toUtf8Bytes("watermarked-csv-commit"));
    const metadataUri = "ipfs://QmExample/metadata.json";
    const chainId = (await ethers.provider.getNetwork()).chainId;

    const inner = structHash(dataHash, minter.address, chainId, address);
    const signature = await signer.signMessage(ethers.getBytes(inner));

    await expect(contract.connect(minter).mint(dataHash, metadataUri, signature))
      .to.emit(contract, "DataAssetMinted")
      .withArgs(minter.address, 1n, dataHash, metadataUri);

    expect(await contract.ownerOf(1n)).to.equal(minter.address);
    expect(await contract.tokenURI(1n)).to.equal(metadataUri);
    expect(await contract.hashMinted(dataHash)).to.equal(true);
  });


// 2. 위조된 서명을 가진 사용자에게 NFT가 발급 차단되는지 확인
  it("mint: 잘못된 서명이면 revert", async function () {
    const { contract, other, minter, address } = await deployFixture();
    const dataHash = ethers.keccak256(ethers.toUtf8Bytes("h2"));
    const metadataUri = "ipfs://x";
    const chainId = (await ethers.provider.getNetwork()).chainId;
    const inner = structHash(dataHash, minter.address, chainId, address);
    const badSig = await other.signMessage(ethers.getBytes(inner));

    await expect(
      contract.connect(minter).mint(dataHash, metadataUri, badSig)
    ).to.be.revertedWith("invalid signature");
  });


// 3. 중복된 데이터셋에 대한 NFT 발급이 차단되는지 확인
  it("mint: 동일 dataHash 재민팅 시 revert", async function () {
    const { contract, signer, minter, address } = await deployFixture();
    const dataHash = ethers.keccak256(ethers.toUtf8Bytes("once"));
    const uri = "ipfs://a";
    const chainId = (await ethers.provider.getNetwork()).chainId;
    const inner = structHash(dataHash, minter.address, chainId, address);
    const sig = await signer.signMessage(ethers.getBytes(inner));

    await contract.connect(minter).mint(dataHash, uri, sig);
    await expect(contract.connect(minter).mint(dataHash, uri, sig)).to.be.revertedWith(
      "hash already minted"
    );
  });


// 4. 인증된 두 사용자 사이에서 NFT 소유권 이전이 정상적으로 이루어지는지 확인
  it("transferFrom: 표준 이전 동작", async function () {
    const { contract, signer, minter, other, address } = await deployFixture();
    const dataHash = ethers.keccak256(ethers.toUtf8Bytes("xfer"));
    const uri = "ipfs://t";
    const chainId = (await ethers.provider.getNetwork()).chainId;
    const inner = structHash(dataHash, minter.address, chainId, address);
    const sig = await signer.signMessage(ethers.getBytes(inner));
    await contract.connect(minter).mint(dataHash, uri, sig);

    await contract.connect(minter).transferFrom(minter.address, other.address, 1n);
    expect(await contract.ownerOf(1n)).to.equal(other.address);
  });


// 5. 관리자가 아닌 유저가 NFT의 소유권을 변경하는 작업이 차단되는지 확인
  it("setAuthorizedSigner: owner만 변경 가능", async function () {
    const { contract, owner, signer, other, minter, address } = await deployFixture();
    await expect(contract.connect(other).setAuthorizedSigner(minter.address)).to.be.revertedWith(
      "Ownable: caller is not the owner"
    );
    await contract.connect(owner).setAuthorizedSigner(minter.address);
    expect(await contract.authorizedSigner()).to.equal(minter.address);

    const dataHash = ethers.keccak256(ethers.toUtf8Bytes("new-signer"));
    const uri = "ipfs://ns";
    const chainId = (await ethers.provider.getNetwork()).chainId;
    const inner = structHash(dataHash, minter.address, chainId, address);
    const sig = await signer.signMessage(ethers.getBytes(inner));
    await expect(contract.connect(minter).mint(dataHash, uri, sig)).to.be.revertedWith("invalid signature");
  });
});
