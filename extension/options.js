const apiKeyInput = document.getElementById("api-key");
const modelInput = document.getElementById("model");
const saved = document.getElementById("saved");

chrome.storage.local.get(["apiKey", "model"]).then(({ apiKey = "", model = "" }) => {
  apiKeyInput.value = apiKey;
  modelInput.value = model;
});

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.local.set({
    apiKey: apiKeyInput.value.trim(),
    model: modelInput.value.trim(),
  });
  saved.hidden = false;
  setTimeout(() => { saved.hidden = true; }, 2000);
});
