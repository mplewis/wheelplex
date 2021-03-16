const oneDaySecs = 60 * 60 * 24;

function epoch() {
  return Number(new Date()) / 1000;
}

async function library() {
  const expiry = JSON.parse(localStorage.libraryExpiry);
  if (localStorage.libraryItems && epoch() < expiry) {
    return JSON.parse(localStorage.libraryItems);
  }
  return await populate();
}

async function populate() {
  const resp = await fetch("/list", { credentials: "same-origin" });
  const data = await resp.json();
  localStorage.libraryItems = JSON.stringify(data);
  localStorage.libraryExpiry = JSON.stringify(epoch() + oneDaySecs);
  return data;
}
