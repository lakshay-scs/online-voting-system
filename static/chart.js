// static/script.js

document.addEventListener("DOMContentLoaded", () => {

    // ======== Confirm vote before submitting ========
    const voteForm = document.querySelector("form[action='/vote']");

    if (voteForm) {
        voteForm.addEventListener("submit", (e) => {
            const selected = voteForm.querySelector("input[name='candidate']:checked");
            if (!selected) {
                alert("⚠️ Please select a candidate before voting!");
                e.preventDefault();
                return;
            }

            const confirmVote = confirm(`You are about to vote for "${selected.value}".\n\nOnce submitted, you cannot change your vote.\n\nDo you want to continue?`);
            if (!confirmVote) {
                e.preventDefault();
            }
        });
    }

    // ======== Live results updater (optional feature) ========
    const resultsTable = document.querySelector("#resultsTable");
    if (resultsTable) {
        setInterval(() => {
            fetch("/results-data")
                .then(res => res.json())
                .then(data => {
                    if (data.count) {
                        resultsTable.innerHTML = "";
                        Object.entries(data.count).forEach(([name, votes]) => {
                            const row = `<tr><td>${name}</td><td>${votes}</td></tr>`;
                            resultsTable.innerHTML += row;
                        });

                        const status = document.getElementById("chainStatus");
                        if (data.valid_chain) {
                            status.innerText = "✅ Blockchain integrity verified — no tampering detected.";
                            status.style.color = "green";
                        } else {
                            status.innerText = "⚠️ Blockchain integrity failed — data may be compromised.";
                            status.style.color = "red";
                        }
                    }
                })
                .catch(err => console.error("Error updating results:", err));
        }, 5000); // refresh every 5 seconds
    }

    // ======== Flash message auto-hide ========
    const flash = document.querySelector(".flash");
    if (flash) {
        setTimeout(() => {
            flash.style.opacity = "0";
            setTimeout(() => flash.remove(), 500);
        }, 4000);
    }
});
