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
        const crown = document.getElementById(`crown-${player_num}`);
        if (crown) {
            crown.style.visibility = "visible";
        }
    });
}

// Show/hide deal-inner option based on winner selection
const winner = document.getElementById("winner");
const deal_inner = document.getElementById("deal_inner");

function syncSelects(changed, other) {
    const selectedValue = changed.value;

    // Reset all options
    for (let option of other.options) {
        option.disabled = false;
    }

    // Hide the selected option
    if (selectedValue) {
        const optionToHide = other.querySelector(`option[value="${selectedValue}"]`);
        if (optionToHide) {
            optionToHide.disabled = true;

            // Reset if both had the same value
            if (other.value === selectedValue) {
                other.value = "";
            }
        }
    }
}

winner.addEventListener("change", () => syncSelects(winner, deal_inner));
deal_inner.addEventListener("change", () => syncSelects(deal_inner, winner));