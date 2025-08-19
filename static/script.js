function toggleDealInner(radio) {
    let extraDiv = document.getElementById("extra-question");
    if (radio.value === "No") {
        extraDiv.style.display = "table-row";
    }else {
        extraDiv.style.display = "none";
    }
}