/** @type import('hardhat/config').HardhatUserConfig */
// 터미널에 npx hardhat compile 입력시 설정에 따라 Hardhat이 DataAsset.sol 컴파일 진행
// 생성된 파일은 artifacts-hardhat/, cache-hardhat/ 디렉토리에서 확인 가능

// 환경변수 불러오기
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, ".env") });

require("@nomicfoundation/hardhat-toolbox");
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  // Sepolia 배포: .env 의 MINTMARK_ADMIN_PRIVATE_KEY (Sepolia ETH 보유 지갑)
  // npx hardhat run scripts/deploy_DataAsset.js --network sepolia
  networks: {
    sepolia: {
      url: process.env.MINTMARK_RPC_URL || "",
      accounts: process.env.MINTMARK_ADMIN_PRIVATE_KEY
        ? [process.env.MINTMARK_ADMIN_PRIVATE_KEY]
        : [],
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test-solidity",
    cache: "./cache-hardhat",
    artifacts: "./artifacts-hardhat",
  },
};
