/** @type import('hardhat/config').HardhatUserConfig */
/// 터미널에 npx hardhat compile 입력시 설정에 따라 Hardhat이 DataAsset.sol 컴파일 진행
/// 생성된 파일은 artifacts-hardhat/, cache-hardhat/ 디렉토리에서 확인 가능

require("@nomicfoundation/hardhat-toolbox");
module.exports = {
  solidity: {
    version: "0.8.20", 
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test-solidity",
    cache: "./cache-hardhat",
    artifacts: "./artifacts-hardhat",
  },
};