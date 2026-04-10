// =================================================================================
// 파일명:   DataAsset.sol
// 목적:     NFT 민팅 스마트 컨트랙트
// =================================================================================


// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// OpenZeppelin에서 기본 NFT 기능을 import
import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721URIStorage} from "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/// @title NFT
/// @notice 원본 데이터셋의 커밋 해시(`dataHash`)를 온체인에 기록하고,
///         `authorizedSigner`의 EIP-191 서명이 있을 때만 민팅을 허용
/// @dev `transfer` / `safeTransferFrom` 은 ERC721 표준 그대로 사용함

contract DataAsset is ERC721URIStorage, Ownable {

    /// @notice 백엔드 서버의 지갑 주소
    address public authorizedSigner;

    /// @notice 다음에 발급할 NFT의 번호
    uint256 private _nextTokenId;

    /// @notice (해시값 -> 발급여부)를 저장하여 동일 데이터로 여러개의 NFT를 발급받는 것을 방지
    mapping(bytes32 => bool) public hashMinted;


    /// 백엔드 서버 지갑 주소 변경 로그 기록(event)
    event AuthorizedSignerUpdated(address indexed previousSigner, address indexed newSigner);
    event DataAssetMinted(
        address indexed to,
        uint256 indexed tokenId,
        bytes32 indexed dataHash,
        string metadataURI
    );


    /// 스마트컨트랙트 배포시 최초 1회 호출
    constructor(address initialOwner, address signer_) ERC721("projectFullName", "projectSideName") {
        require(initialOwner != address(0), "owner zero");
        require(signer_ != address(0), "signer zero");
        authorizedSigner = signer_;
        _nextTokenId = 1;
        _transferOwnership(initialOwner);
    }


    /// 스마트컨트랙트의 Owner만 호출 가능한 signer 교체 함수
    /// 백엔드 서버 이전, 또는 서버 지갑 주소 해킹 등의 사고 발생시 서버를 재설정 하기 위해 필요
    function setAuthorizedSigner(address signer_) external onlyOwner {
        require(signer_ != address(0), "signer zero");
        /// 체인상에 서버 주소 변경 로그를 브로드캐스팅(위에서 정의한 AuthorizedSignerUpdated 호출)
        emit AuthorizedSignerUpdated(authorizedSigner, signer_);
        authorizedSigner = signer_;
    }


    /// @notice 서명 대상: keccak256(abi.encode(dataHash, minter, chainId, address(this)))
    ///         오프체인에서 동일한 방식으로 structHash를 만든 뒤 EIP-191로 서명 필요
    function mint(
        bytes32 dataHash,
        string calldata metadataUri,
        bytes calldata signature
    ) external returns (uint256 tokenId) {
        /// NFT 발급 대상 데이터셋의 해시값을 통해 이미 NFT가 발급된 데이터셋인지 확인
        require(!hashMinted[dataHash], "hash already minted");
        require(bytes(metadataUri).length > 0, "empty uri");

        /// 사용자의 signature가 authorizedSigner가 발급한 서명이 맞는지 확인
        bytes32 structHash = keccak256(
            abi.encode(dataHash, msg.sender, block.chainid, address(this))
        );
        bytes32 digest = ECDSA.toEthSignedMessageHash(structHash);
        address recovered = ECDSA.recover(digest, signature);
        require(recovered == authorizedSigner, "invalid signature");

        /// 서명 검증 완료 후 NFT 발급
        tokenId = _nextTokenId++;   
        hashMinted[dataHash] = true;   
        _safeMint(msg.sender, tokenId);
        _setTokenURI(tokenId, metadataUri);

        emit DataAssetMinted(msg.sender, tokenId, dataHash, metadataUri);
    }

    /// @dev 소유권 이전은 IERC721.transferFrom / safeTransferFrom 사용 (표준)
}