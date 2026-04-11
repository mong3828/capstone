/**
 * DataAsset 배포 (Sepolia)
 *
 * .env: B2MARK_RPC_URL, B2MARK_ADMIN_PRIVATE_KEY (가스·배포·Owner·authorizedSigner 모두 동일 지갑)
 *
 * 생성자(initialOwner, authorizedSigner) 는 배포 지갑 주소로 동일 설정합니다.
 */
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const addr = deployer.address;

  console.log("Deployer / Owner / authorizedSigner (same wallet):", addr);

  const Factory = await hre.ethers.getContractFactory("DataAsset");
  const contract = await Factory.deploy(addr, addr);
  await contract.waitForDeployment();
  const deployed = await contract.getAddress();
  console.log("DataAsset deployed to:", deployed);
  console.log("Set B2MARK_CONTRACT_ADDRESS=" + deployed + " in .env for CLI mint.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
