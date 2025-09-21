document.addEventListener("DOMContentLoaded", () => {
    const submitBtn = document.querySelector(".submit-btn");
    let selectedDisaster = "";
    let selectedLevel = "";

    // Handle disaster selection
    window.selectDisaster = (disaster) => {
        selectedDisaster = disaster;

        // Highlight selected disaster button
        document.querySelectorAll('.disaster-btn').forEach(btn => btn.classList.remove('selected'));
        document.querySelectorAll('.disaster-btn').forEach(btn => {
            if (btn.textContent.toLowerCase() === disaster) btn.classList.add('selected');
        });

        // Show or hide water level section depending on disaster
        const waterLevelSection = document.getElementById("water-level-section");
        if (disaster === "flood") {
            waterLevelSection.style.display = "block";
        } else {
            waterLevelSection.style.display = "none";
            selectedLevel = ""; // reset water level
            document.querySelectorAll('.level-btn').forEach(btn => btn.classList.remove('selected'));
        }
    };

    // Track selected water level
    window.selectLevel = (level) => {
        selectedLevel = level;
        const buttons = document.querySelectorAll('.level-btn');
        buttons.forEach(btn => btn.classList.remove('selected'));
        document.querySelector(`.level-btn.${level}`).classList.add('selected');
    };

    submitBtn.addEventListener("click", async () => {
        const locationInput = document.querySelector(".location-input").value.trim();
        let missingFields = [];

        // Validate disaster type
        if (!selectedDisaster) {
            missingFields.push("disaster type");
        }

        // If disaster is Flood, validate water level and location
        if (selectedDisaster === "flood") {
            if (!selectedLevel) missingFields.push("water level");
            if (!locationInput) missingFields.push("flood location");
        }

        if (missingFields.length > 0) {
            alert("Please fill in the following fields: " + missingFields.join(", "));
            return;
        }

        // Build data object
        const userProfile = { userId: "U12345", name: "Charlotte Chen" };
        const dataToSend = {
            profile: userProfile,
            disasterType: selectedDisaster,
            waterLevel: selectedDisaster === "flood" ? selectedLevel : null,
            location: selectedDisaster === "flood" ? locationInput : null,
            timestamp: new Date().toISOString()
        };

        // For Flood, get geolocation
        if (selectedDisaster === "flood" && navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    dataToSend.geotag = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude
                    };
                    sendReport(dataToSend);
                },
                (err) => alert("Failed to get location: " + err.message)
            );
        } else {
            // Non-flood disasters
            sendReport(dataToSend);
        }
    });

    async function sendReport(data) {
        try {
            const response = await fetch("https://your-server-endpoint.com/report", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-api-key": "YOUR_API_KEY"
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                alert("Report submitted successfully!");
            } else {
                alert("Failed to submit report.");
            }
        } catch (error) {
            console.error(error);
            alert("Error sending report.");
        }
    }

});
