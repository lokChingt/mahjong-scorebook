// Function to toggle the extra question row based on self-drawn selection
function toggleDealInner(radio) {
    let extraQs = document.getElementById("extra-question");
    if (radio.value === "No") {
        extraQs.style.display = "table-row";
    }else {
        extraQs.style.display = "none";
    }
}

// Function to show the crown for the given player_id
function showCrownForLeader(playerId) {
    playerId.forEach((id) => {
        console.log("Leading player ID:", id);
        const crown = document.getElementById(`crown-${id}`);
        if (crown) {
            crown.style.visibility = "visible";
        }
    });
}