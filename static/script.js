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
function showCrownForLeader(players) {
    players.forEach((player_num) => {
        console.log("Leading player ID:", player_num);
        const crown = document.getElementById(`crown-${player_num}`);
        if (crown) {
            crown.style.visibility = "visible";
        }
    });
}