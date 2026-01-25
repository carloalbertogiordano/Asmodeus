const hre = require("hardhat");
const { expect } = require("chai");

describe("KeyReconstruction Contract", function () {
  let contract;
  let deployer, user1, user2;
  let keyID;

  beforeEach(async function () {
    [deployer, user1, user2] = await hre.ethers.getSigners();

    const threshold = 2;
    const KeyReconstruction = await hre.ethers.getContractFactory("KeyReconstruction");
    contract = await KeyReconstruction.deploy(deployer.address, threshold);
    await contract.waitForDeployment();

    keyID = hre.ethers.encodeBytes32String("session1"); // <-- ethers v6
  });

  it("Should prepare a session", async function () {
    await expect(contract.connect(user1).prepare(keyID))
      .to.emit(contract, "Prepare")
      .withArgs(keyID, user1.address);

    const session = await contract.sessions(keyID);
    expect(session.exists).to.be.true;
    expect(session.creator).to.equal(user1.address);
  });

  it("Should submit shares", async function () {
    await contract.connect(user1).prepare(keyID);

    const share1 = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("share1"));
    const share2 = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("share2"));

    await expect(contract.connect(user1).submitShare(keyID, share1))
      .to.emit(contract, "ShareSubmitted")
      .withArgs(keyID, user1.address, share1);

    await expect(contract.connect(user2).submitShare(keyID, share2))
      .to.emit(contract, "ShareSubmitted")
      .withArgs(keyID, user2.address, share2);

    const participants = await contract.getParticipants(keyID);
    expect(participants.length).to.equal(2);

    const shareHashes = await contract.getShareHashes(keyID);
    expect(shareHashes.length).to.equal(2);
  });

  it("Should submit proof only by server and threshold reached", async function () {
    await contract.connect(user1).prepare(keyID);

    const share1 = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("share1"));
    const share2 = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("share2"));

    await contract.connect(user1).submitShare(keyID, share1);
    await contract.connect(user2).submitShare(keyID, share2);

    const ciphertextHashes = [
      hre.ethers.keccak256(hre.ethers.toUtf8Bytes("ciphertext1")),
      hre.ethers.keccak256(hre.ethers.toUtf8Bytes("ciphertext2")),
    ];

    await expect(contract.connect(deployer).submitProof(keyID, ciphertextHashes))
      .to.emit(contract, "KeyReconstructed")
      .withArgs(keyID);

    const session = await contract.sessions(keyID);
    expect(session.closed).to.be.true;

    const storedCiphertextHashes = await contract.getCiphertextHashes(keyID);
    expect(storedCiphertextHashes.length).to.equal(2);

    await expect(contract.connect(user1).submitProof(keyID, ciphertextHashes))
      .to.be.revertedWith("Only server can submit proof");
  });
});
