// Hover or tap a year dot (YearDots.tsx) to read its year and value; leaving puts back the rank sentence. One
// delegated listener for the whole page, since the dots are static SVG with no island of their own.
function readout(target: EventTarget | null, leaving = false) {
  const dot = (target as Element | null)?.closest?.(".yeardots circle[data-say]");
  const box = (target as Element | null)?.closest?.(".yeardots") as HTMLElement | null;
  if (!box) return;
  const read = box.querySelector(".yd-read");
  if (!read) return;
  box.querySelectorAll("circle[data-on]").forEach((c) => c.removeAttribute("data-on"));
  if (dot && !leaving) { read.textContent = dot.getAttribute("data-say"); dot.setAttribute("data-on", ""); }
  else read.textContent = box.dataset.default ?? "";
}
document.addEventListener("pointerover", (e) => readout(e.target));
document.addEventListener("pointerout", (e) => { if (!(e.relatedTarget as Element | null)?.closest?.(".yeardots")) readout(e.target, true); });
document.addEventListener("click", (e) => readout(e.target));
