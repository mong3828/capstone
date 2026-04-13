import { ethers } from "https://esm.sh/ethers@6.13.4";

const SEPOLIA = 11155111n;

function apiBase() {
  return document.getElementById("apiBase").value.replace(/\/$/, "");
}

function log(obj) {
  const el = document.getElementById("out");
  const line = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  el.textContent = line + "\n\n" + el.textContent;
}

async function apiJson(path, { method = "GET", body, token, headers = {} } = {}) {
  const h = { ...headers };
  if (token) h.Authorization = `Bearer ${token}`;
  if (body !== undefined && !h["Content-Type"]) h["Content-Type"] = "application/json";
  const r = await fetch(`${apiBase()}${path}`, {
    method,
    headers: h,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await r.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    const msg = data && data.error ? data.error.message : text;
    throw new Error(`${r.status} ${msg}`);
  }
  return data;
}

let lastNonce = null;
let lastMessage = null;
let accessToken = null;
let refreshToken = null;

document.getElementById("btnHealth").onclick = async () => {
  try {
    const j = await apiJson("/health");
    log(j);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnConnect").onclick = async () => {
  try {
    const eth = window.ethereum;
    if (!eth) throw new Error("window.ethereum 없음 — MetaMask 설치 필요");
    await eth.request({ method: "eth_requestAccounts" });
    const provider = new ethers.BrowserProvider(eth);
    const net = await provider.getNetwork();
    if (net.chainId !== SEPOLIA) {
      await eth.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: "0xaa36a7" }],
      });
    }
    const signer = await provider.getSigner();
    const addr = await signer.getAddress();
    document.getElementById("wallet").value = addr;
    log({ connected: addr, chainId: String(net.chainId) });
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnNonce").onclick = async () => {
  try {
    const wallet = document.getElementById("wallet").value.trim();
    if (!wallet) throw new Error("먼저 MetaMask 연결");
    const data = await apiJson("/auth/nonce", {
      method: "POST",
      body: { walletAddress: wallet },
    });
    lastNonce = data.nonce;
    lastMessage = data.message;
    log(data);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnLogin").onclick = async () => {
  try {
    const wallet = document.getElementById("wallet").value.trim();
    if (!lastMessage || !lastNonce) throw new Error("먼저 POST /auth/nonce");
    const eth = window.ethereum;
    if (!eth) throw new Error("MetaMask 없음");
    const provider = new ethers.BrowserProvider(eth);
    const signer = await provider.getSigner();
    const sig = await signer.signMessage(lastMessage);
    const data = await apiJson("/auth/login", {
      method: "POST",
      body: { walletAddress: wallet, signature: sig, nonce: lastNonce },
    });
    accessToken = data.accessToken;
    refreshToken = data.refreshToken;
    log({ ok: true, accessToken: accessToken.slice(0, 24) + "…", refreshToken: refreshToken.slice(0, 24) + "…" });
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnRefresh").onclick = async () => {
  try {
    if (!refreshToken) throw new Error("refreshToken 없음 — 먼저 login");
    const data = await apiJson("/auth/refresh", {
      method: "POST",
      body: { refreshToken },
    });
    accessToken = data.accessToken;
    refreshToken = data.refreshToken;
    log({ refreshed: true });
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnLogout").onclick = async () => {
  try {
    if (!refreshToken) throw new Error("refreshToken 없음");
    await apiJson("/auth/logout", {
      method: "POST",
      body: { refreshToken },
    });
    refreshToken = null;
    accessToken = null;
    log({ loggedOut: true });
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnMeGet").onclick = async () => {
  try {
    if (!accessToken) throw new Error("accessToken 없음");
    const data = await apiJson("/users/me", { token: accessToken });
    log(data);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnMePatch").onclick = async () => {
  try {
    if (!accessToken) throw new Error("accessToken 없음");
    const name = document.getElementById("patchName").value;
    const data = await apiJson("/users/me", {
      method: "PATCH",
      token: accessToken,
      body: { name },
    });
    log(data);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnNftCreate").onclick = async () => {
  try {
    if (!accessToken) throw new Error("accessToken 없음");
    const name = document.getElementById("nftName").value || "NFT";
    const data = await apiJson("/nfts", {
      method: "POST",
      token: accessToken,
      body: { name, description: "webtest" },
    });
    document.getElementById("nftId").value = data.id;
    log(data);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnNftList").onclick = async () => {
  try {
    if (!accessToken) throw new Error("accessToken 없음");
    const page = document.getElementById("page").value || "1";
    const pageSize = document.getElementById("pageSize").value || "20";
    const st = document.getElementById("nftStatus").value.trim();
    const chainId = document.getElementById("chainId").value.trim();
    let q = `?page=${encodeURIComponent(page)}&pageSize=${encodeURIComponent(pageSize)}`;
    if (st) q += `&status=${encodeURIComponent(st)}`;
    if (chainId) q += `&chainId=${encodeURIComponent(chainId)}`;
    const data = await apiJson(`/nfts${q}`, { token: accessToken });
    log(data);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnNftGet").onclick = async () => {
  try {
    if (!accessToken) throw new Error("accessToken 없음");
    const id = document.getElementById("nftId").value.trim();
    if (!id) throw new Error("nft id 입력");
    const data = await apiJson(`/nfts/${encodeURIComponent(id)}`, { token: accessToken });
    log(data);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnNftPatch").onclick = async () => {
  try {
    if (!accessToken) throw new Error("accessToken 없음");
    const id = document.getElementById("nftId").value.trim();
    if (!id) throw new Error("nft id 입력");
    const body = {
      status: "MINTED",
      tokenId: "1",
      contractAddress: "0x0000000000000000000000000000000000000001",
      mintTxHash: "0x" + "ab".repeat(32),
      metadataUri: "ipfs://test",
    };
    const data = await apiJson(`/nfts/${encodeURIComponent(id)}`, {
      method: "PATCH",
      token: accessToken,
      body,
    });
    log(data);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnWatermarkAnon").onclick = async () => {
  try {
    const f = document.getElementById("wmFile").files[0];
    if (!f) throw new Error("CSV 파일 선택");
    const fd = new FormData();
    fd.append("file", f, f.name);
    fd.append("buyer_id", document.getElementById("wmBuyer").value);
    fd.append("target", document.getElementById("wmTarget").value);
    fd.append("ref_cols", document.getElementById("wmRef").value);
    fd.append("secret_key", document.getElementById("wmSecret").value);
    fd.append("k", "10");
    fd.append("g", "3");
    fd.append("embed_seed", "10000");
    const r = await fetch(`${apiBase()}/watermark`, { method: "POST", body: fd });
    if (!r.ok) {
      const t = await r.text();
      let err = t;
      try {
        const j = JSON.parse(t);
        if (j.error) err = j.error.message;
      } catch {}
      throw new Error(`${r.status} ${err}`);
    }
    const blob = await r.blob();
    log(`watermark OK, ${blob.size} bytes CSV 다운로드 생략(콘솔만)`);
  } catch (e) {
    log(String(e));
  }
};

document.getElementById("btnWatermarkNft").onclick = async () => {
  try {
    if (!accessToken) throw new Error("accessToken 없음");
    const id = document.getElementById("nftId").value.trim();
    if (!id) throw new Error("nft id 입력");
    const f = document.getElementById("wmFile").files[0];
    if (!f) throw new Error("CSV 파일 선택");
    const fd = new FormData();
    fd.append("file", f, f.name);
    fd.append("buyer_id", document.getElementById("wmBuyer").value);
    fd.append("target", document.getElementById("wmTarget").value);
    fd.append("ref_cols", document.getElementById("wmRef").value);
    fd.append("secret_key", document.getElementById("wmSecret").value);
    fd.append("k", "10");
    fd.append("g", "3");
    fd.append("embed_seed", "10000");
    const r = await fetch(`${apiBase()}/nfts/${encodeURIComponent(id)}/watermark`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: fd,
    });
    if (!r.ok) {
      const t = await r.text();
      let err = t;
      try {
        const j = JSON.parse(t);
        if (j.error) err = j.error.message;
      } catch {}
      throw new Error(`${r.status} ${err}`);
    }
    const blob = await r.blob();
    log(`NFT watermark OK, ${blob.size} bytes (NFT에 watermarkedDataHash 저장됨)`);
  } catch (e) {
    log(String(e));
  }
};
