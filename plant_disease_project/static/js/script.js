// hiding register form by making login form active 
function showForm(formId){
    const forms = document.querySelectorAll(".form-box");
    forms.forEach(form => form.classList.remove("active"));

    const selectedForm = document.getElementById(formId);
    if(selectedForm){
        selectedForm.classList.add("active");
    }
}


// login — POST to Django /login/
const loginForm = document.querySelector("#login-form form");

if(loginForm){
    loginForm.addEventListener("submit", async function(e){ 
        e.preventDefault();

        const errorBox = document.getElementById("login-error");
        errorBox.style.display = "none";

        const formData = new FormData(this);

        try {
            const res  = await fetch("/login/", {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN },
                body: formData,
            });
            const data = await res.json();

            if(data.success){
                window.location.href = data.redirect;
            } else {
                errorBox.textContent   = data.error || "Login failed.";
                errorBox.style.display = "block";
            }
        } catch(err) {
            errorBox.textContent   = "Network error. Please try again.";
            errorBox.style.display = "block";
        }
    });
}


// register — POST to Django /register/
const registerForm = document.querySelector("#register-form form");

if(registerForm){
    registerForm.addEventListener("submit", async function(e){
        e.preventDefault();

        const errorBox   = document.getElementById("register-error");
        const successBox = document.getElementById("register-success");
        errorBox.style.display   = "none";
        successBox.style.display = "none";

        const formData        = new FormData(this);
        const password        = formData.get("password");
        const confirmPassword = formData.get("confirmpassword");

        if(password !== confirmPassword){
            errorBox.textContent   = "Passwords do not match";
            errorBox.style.display = "block";
            return;
        }

        try {
            const res  = await fetch("/register/", {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN },
                body: formData,
            });
            const data = await res.json();

            if(data.success){
                successBox.textContent   = data.message || "Registered successfully!";
                successBox.style.display = "block";
                registerForm.reset();
                setTimeout(() => showForm("login-form"), 1500);
            } else {
                errorBox.textContent   = data.error || "Registration failed.";
                errorBox.style.display = "block";
            }
        } catch(err) {
            errorBox.textContent   = "Network error. Please try again.";
            errorBox.style.display = "block";
        }
    });
}


// nav link menu on small screen 
const navLinks = document.getElementById("navLinks");

function showMenu(){
    if(navLinks){
        navLinks.style.right = "0";
    }
}

function hideMenu(){
    if(navLinks){
        navLinks.style.right = "-200px";
    }
}


// image preview 
const fileInput = document.getElementById("fileInput");
const preview   = document.getElementById("preview");

if(fileInput && preview){
    fileInput.addEventListener("change", function(){
        const file = this.files[0];

        if(file){
            const reader = new FileReader();

            reader.onload = function(e){
                preview.src           = e.target.result;
                preview.style.display = "block";
            }

            reader.readAsDataURL(file);
            
            // Clear camera capture when file is uploaded
            capturedBlob = null;
        }
    });
}


// live camera 
let cameraStream = null;
let capturedBlob = null;   // stores camera capture as Blob for upload

function startCamera() {
    const video      = document.getElementById("camera");
    const captureBtn = document.getElementById("captureBtn");

    // Clear previous captures
    capturedBlob = null;
    preview.src = "";
    preview.style.display = "none";
    fileInput.value = "";

    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            cameraStream             = stream;
            video.srcObject          = stream;
            video.style.display      = "block";
            captureBtn.style.display = "inline-block";
        })
        .catch(() => {
            alert("Camera access denied!");
        });
}

function captureImage() {
    const video   = document.getElementById("camera");
    const preview = document.getElementById("preview");

    const canvas = document.createElement("canvas");
    const ctx    = canvas.getContext("2d");

    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0);

    const imageData = canvas.toDataURL("image/png");

    preview.src           = imageData;
    preview.style.display = "block";

    // save as Blob so analyzeImage() can upload it
    canvas.toBlob(blob => { capturedBlob = blob; }, "image/png");

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }

    video.style.display = "none";
    document.getElementById("captureBtn").style.display = "none";
}


// analysis — POST to Django /analyze/
async function analyzeImage() {
    const fileInput = document.getElementById("fileInput");
    const preview   = document.getElementById("preview");

    if (!fileInput.files.length && preview.style.display === "none") {
        alert("Please upload or capture an image first.");
        return;
    }

    let existingResult = document.getElementById("result-box");
    if (existingResult) existingResult.remove();

    const resultSection = document.createElement("section");
    resultSection.className = "result-section";

    const resultBox = document.createElement("div");
    resultBox.id        = "result-box";
    resultBox.className = "result-box";
    resultBox.innerHTML = "<p>Analyzing image... ⏳</p>";

    resultSection.appendChild(resultBox);

    const uploadSection = document.getElementById("upload");
    uploadSection.insertAdjacentElement("afterend", resultSection);

    // Scroll to result box
    resultBox.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // build FormData with the image
    const formData = new FormData();
    if(fileInput.files.length){
        formData.append("image", fileInput.files[0]);
    } else if(capturedBlob){
        formData.append("image", capturedBlob, "camera_capture.png");
    }

    try {
        const res  = await fetch("/analyze/", {
            method: "POST",
            headers: { "X-CSRFToken": CSRF_TOKEN },
            body: formData,
        });
        const data = await res.json();

        if(data.success){
            if(data.status === "stub"){
                resultBox.innerHTML = `
                    <h3>Analysis Result</h3>
                    <p>Model is still being trained.</p>
                    <p><b>Note:</b> Your image was saved. Results will be available once the model is ready.</p>
                    <p><small>Scan ID: #${data.scan_id}</small></p>
                `;
            } else if(data.is_leaf === false || data.disease_name === "Not a leaf") {
                const errorMsg = data.leaf_error ? `<p style="color:orange;"><small>${data.leaf_error}</small></p>` : '';
                resultBox.innerHTML = `
                    <h3>Object detected: Not a leaf</h3>
                    <p>Please upload an image of a plant leaf.</p>
                    <p><b>Leaf model decision:</b> ${data.leaf_label || 'N/A'} (${data.leaf_confidence ? (data.leaf_confidence * 100).toFixed(1) + '%' : 'N/A'})</p>
                    ${errorMsg}
                    <p><small>Scan ID: #${data.scan_id}</small></p>
                `;
            } else {
                const rec = data.recommendation || {};
                resultBox.innerHTML = `
                    <h3>Disease: ${data.disease_name}</h3>
                    <p><b>Confidence:</b> ${data.confidence}</p>
                    
                    <div class="recommendation-box">
                        <h4>💡 Recommendations</h4>
                        <div class="rec-section">
                            <strong>Treatment:</strong>
                            <p>${rec.treatment || 'Not available'}</p>
                        </div>
                        <div class="rec-section">
                            <strong>Prevention:</strong>
                            <p>${rec.prevention || 'Not available'}</p>
                        </div>
                        ${rec.organic ? `
                        <div class="rec-section">
                            <strong>🌿 Organic Option:</strong>
                            <p>${rec.organic}</p>
                        </div>
                        ` : ''}
                    </div>
                    
                    <p><small>Scan ID: #${data.scan_id}</small></p>
                `;
            }
        } else {
            resultBox.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
        }

    } catch(err) {
        resultBox.innerHTML = `<p style="color:red;">Network error. Please try again.</p>`;
    }
}


// user activity session 
const userIcon     = document.getElementById("userIcon");
const userDropdown = document.getElementById("userDropdown");

if(userIcon && userDropdown){
    userIcon.addEventListener("click", () => {
        userDropdown.style.display =
            userDropdown.style.display === "flex" ? "none" : "flex";
    });

    window.addEventListener("click", (e) => {
        if(!userIcon.contains(e.target) && !userDropdown.contains(e.target)){
            userDropdown.style.display = "none";
        }
    });
}

// username is now set by Django template directly — no localStorage needed
// logout is now a real link in the template — no JS needed


// password reset request — POST to /password-reset/
const passwordResetRequestForm = document.getElementById("passwordResetRequestForm");

if(passwordResetRequestForm){
    passwordResetRequestForm.addEventListener("submit", async function(e){
        e.preventDefault();

        const errorBox   = document.getElementById("reset-error");
        const successBox = document.getElementById("reset-success");
        errorBox.style.display   = "none";
        successBox.style.display = "none";

        const formData = new FormData(this);

        try {
            const res  = await fetch("/password-reset/", {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN },
                body: formData,
            });
            const data = await res.json();

            if(data.success){
                successBox.textContent   = data.message || "Reset link sent! Check your email.";
                successBox.style.display = "block";
                passwordResetRequestForm.reset();
            } else {
                errorBox.textContent   = data.error || "Failed to send reset link.";
                errorBox.style.display = "block";
            }
        } catch(err) {
            errorBox.textContent   = "Network error. Please try again.";
            errorBox.style.display = "block";
        }
    });
}


// password reset confirm — POST to /password-reset/<token>/
const passwordResetConfirmForm = document.getElementById("passwordResetConfirmForm");

if(passwordResetConfirmForm){
    passwordResetConfirmForm.addEventListener("submit", async function(e){
        e.preventDefault();

        const errorBox   = document.getElementById("reset-confirm-error");
        const successBox = document.getElementById("reset-confirm-success");
        errorBox.style.display   = "none";
        successBox.style.display = "none";

        const formData        = new FormData(this);
        const password        = formData.get("password");
        const confirmPassword = formData.get("confirm_password");

        if(password !== confirmPassword){
            errorBox.textContent   = "Passwords do not match";
            errorBox.style.display = "block";
            return;
        }

        try {
            const res  = await fetch(window.location.href, {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN },
                body: formData,
            });
            const data = await res.json();

            if(data.success){
                successBox.textContent   = data.message || "Password reset successfully!";
                successBox.style.display = "block";
                passwordResetConfirmForm.reset();
                setTimeout(() => {
                    window.location.href = "/";
                }, 1500);
            } else {
                errorBox.textContent   = data.error || "Failed to reset password.";
                errorBox.style.display = "block";
            }
        } catch(err) {
            errorBox.textContent   = "Network error. Please try again.";
            errorBox.style.display = "block";
        }
    });
}