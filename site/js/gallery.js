// The front page: a grid of every model, with Creatures and Items tabs and a search over names.
// Nothing 3D is loaded here; each tile is a still picture and a link to the model's page.
(async function () {
  const grid = document.getElementById("grid");
  const search = document.getElementById("search");
  const count = document.getElementById("count");
  const tabs = [...document.querySelectorAll(".tabs button")];
  const models = await (await fetch("data/models.json")).json();
  const params = new URLSearchParams(location.search);   // kind=item, q=search
  let kind = params.get("kind") === "item" ? "item" : "creature";
  search.value = params.get("q") || "";

  function show() {
    const q = search.value.trim().toLowerCase();
    tabs.forEach(t => t.setAttribute("aria-selected", String(t.dataset.kind === kind)));
    const list = models.filter(m => m.kind === kind && (!q || m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q)));
    grid.replaceChildren(...list.map(tile));
    count.textContent = `${list.length} ${kind === "creature" ? "creatures" : "items"}${q ? " found" : ""}`;
  }

  function tile(m) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `model.html?id=${encodeURIComponent(m.key)}`;
    const img = document.createElement("img");
    img.src = m.thumb;
    img.alt = "";
    img.loading = "lazy";
    img.width = 160;
    img.height = 160;
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = m.name;
    a.append(img, name);
    if (m.variant_of) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = "variant";
      a.append(badge);
    }
    li.append(a);
    return li;
  }

  tabs.forEach(t => t.addEventListener("click", () => {
    kind = t.dataset.kind;
    history.replaceState(null, "", kind === "item" ? "?kind=item" : "./");
    show();
  }));
  search.addEventListener("input", show);
  show();
})();
