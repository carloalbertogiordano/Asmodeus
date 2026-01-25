const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

module.exports = buildModule("KeyReconstructionModule", (m) => {
  const serverPubKey = m.getParameter("serverPubKey", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"); // Default to Hardhat's first account
  const threshold = m.getParameter("threshold", 2);

  const keyReconstruction = m.contract("KeyReconstruction", [serverPubKey, threshold]);

  return { keyReconstruction };
});