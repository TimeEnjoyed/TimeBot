document.addEventListener("DOMContentLoaded", () => {
    setTab(0);
});


function setTab(index) {

    const TABS = document.querySelectorAll(".queueContent");
    for (let i = 0; i < TABS.length; i++) {
        let inner = TABS[i];
        let tab = document.getElementById(`tab${i}`);

        if (i === index) {
            inner.style.display = "flex";
            tab.style.backgroundColor = "var(--background-secondary)";
        } else {
            inner.style.display = "none";
            tab.style.backgroundColor = "transparent";
        }
    }
}