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
const cameraInput = document.getElementById("cameraInput");
const preview   = document.getElementById("preview");
const cropEditor = document.getElementById("cropEditor");
const cropViewport = document.getElementById("cropViewport");
const cropFrame = document.getElementById("cropFrame");
const cropImage = document.getElementById("cropImage");
const cropZoom = document.getElementById("cropZoom");
const applyCropBtn = document.getElementById("applyCropBtn");
const resetCropBtn = document.getElementById("resetCropBtn");

let cameraFile = null;
let croppedImageBlob = null;
let originalImageSource = "";
let cropState = {
    naturalWidth: 0,
    naturalHeight: 0,
    scale: 1,
    minScale: 1,
    left: 0,
    top: 0,
    dragging: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    startLeft: 0,
    startTop: 0,
};

function showPreview(source) {
    if(preview){
        preview.src = source;
        preview.style.display = "block";
    }
}

function hidePreview() {
    if(preview){
        preview.src = "";
        preview.style.display = "none";
    }
}

function clampCropPosition() {
    if(!cropViewport || !cropState.naturalWidth || !cropState.naturalHeight){
        return;
    }

    const frameWidth = cropFrame ? cropFrame.clientWidth : cropViewport.clientWidth;
    const frameHeight = cropFrame ? cropFrame.clientHeight : cropViewport.clientHeight;
    const frameLeft = cropFrame ? cropFrame.offsetLeft : 0;
    const frameTop = cropFrame ? cropFrame.offsetTop : 0;
    const renderedWidth = cropState.naturalWidth * cropState.scale;
    const renderedHeight = cropState.naturalHeight * cropState.scale;

    const minLeft = frameLeft + frameWidth - renderedWidth;
    const minTop = frameTop + frameHeight - renderedHeight;
    const maxLeft = frameLeft;
    const maxTop = frameTop;

    cropState.left = Math.min(maxLeft, Math.max(minLeft, cropState.left));
    cropState.top = Math.min(maxTop, Math.max(minTop, cropState.top));
}

function renderCropImage() {
    if(!cropViewport || !cropImage || !cropState.naturalWidth || !cropState.naturalHeight){
        return;
    }

    clampCropPosition();

    cropImage.style.width = `${cropState.naturalWidth * cropState.scale}px`;
    cropImage.style.height = `${cropState.naturalHeight * cropState.scale}px`;
    cropImage.style.left = `${cropState.left}px`;
    cropImage.style.top = `${cropState.top}px`;
}

function resetCropPosition() {
    if(!cropViewport || !cropState.naturalWidth || !cropState.naturalHeight){
        return;
    }

    const frameWidth = cropFrame ? cropFrame.clientWidth : cropViewport.clientWidth;
    const frameHeight = cropFrame ? cropFrame.clientHeight : cropViewport.clientHeight;
    const frameLeft = cropFrame ? cropFrame.offsetLeft : 0;
    const frameTop = cropFrame ? cropFrame.offsetTop : 0;
    const renderedWidth = cropState.naturalWidth * cropState.scale;
    const renderedHeight = cropState.naturalHeight * cropState.scale;

    cropState.left = frameLeft + ((frameWidth - renderedWidth) / 2);
    cropState.top = frameTop + ((frameHeight - renderedHeight) / 2);
    renderCropImage();
}

function syncCropZoom(nextZoomValue) {
    if(!cropViewport || !cropState.naturalWidth || !cropState.naturalHeight){
        return;
    }

    const frameWidth = cropFrame ? cropFrame.clientWidth : cropViewport.clientWidth;
    const frameHeight = cropFrame ? cropFrame.clientHeight : cropViewport.clientHeight;
    const focusX = cropFrame ? cropFrame.offsetLeft + (frameWidth / 2) : cropViewport.clientWidth / 2;
    const focusY = cropFrame ? cropFrame.offsetTop + (frameHeight / 2) : cropViewport.clientHeight / 2;
    const previousScale = cropState.scale;
    const nextScale = cropState.minScale * Number(nextZoomValue);
    const imageX = (focusX - cropState.left) / previousScale;
    const imageY = (focusY - cropState.top) / previousScale;

    cropState.scale = nextScale;
    cropState.left = focusX - (imageX * nextScale);
    cropState.top = focusY - (imageY * nextScale);
    renderCropImage();
}

function getBaseCropScale() {
    if(!cropViewport || !cropState.naturalWidth || !cropState.naturalHeight){
        return 1;
    }

    const frameWidth = cropFrame ? cropFrame.clientWidth : cropViewport.clientWidth;
    const frameHeight = cropFrame ? cropFrame.clientHeight : cropViewport.clientHeight;
    const widthRatio = frameWidth / cropState.naturalWidth;
    const heightRatio = frameHeight / cropState.naturalHeight;

    return Math.min(1, widthRatio, heightRatio);
}

function resetCropState() {
    cropState.naturalWidth = 0;
    cropState.naturalHeight = 0;
    cropState.scale = 1;
    cropState.minScale = 1;
    cropState.left = 0;
    cropState.top = 0;
    cropState.dragging = false;
    cropState.pointerId = null;
    cropState.startX = 0;
    cropState.startY = 0;
    cropState.startLeft = 0;
    cropState.startTop = 0;
}

function initializeCropper(source) {
    if(!cropEditor || !cropImage || !cropZoom){
        return;
    }

    croppedImageBlob = null;
    resetCropState();
    cropZoom.value = "1";
    cropEditor.style.display = "flex";
    hidePreview();

    cropImage.removeAttribute("src");
    cropImage.style.width = "";
    cropImage.style.height = "";
    cropImage.style.left = "0";
    cropImage.style.top = "0";

    requestAnimationFrame(() => {
        cropImage.src = source;
    });
}

function handleFileSelect(file, isCamera = false) {
    if(file){
        const reader = new FileReader();

        reader.onload = function(e){
            croppedImageBlob = null;
            originalImageSource = e.target.result;
            initializeCropper(e.target.result);
        };

        reader.readAsDataURL(file);
        
        if(isCamera){
            cameraFile = file;
            fileInput.value = "";
        } else {
            cameraFile = null;
        }
    }
}

if(cropImage){
    cropImage.addEventListener("load", function(){
        if(!cropViewport){
            return;
        }

        cropState.naturalWidth = cropImage.naturalWidth;
        cropState.naturalHeight = cropImage.naturalHeight;
        cropState.minScale = getBaseCropScale();
        cropState.scale = cropState.minScale * Number(cropZoom.value || 1);
        resetCropPosition();
    });
}

if(fileInput && preview){
    fileInput.addEventListener("click", function(){
        this.value = "";
    });

    fileInput.addEventListener("change", function(){
        handleFileSelect(this.files[0], false);
    });
}

if(cameraInput && preview){
    cameraInput.addEventListener("change", function(){
        const file = this.files[0];
        if(file){
            handleFileSelect(file, true);
        }
        this.value = "";
    });
}

const openCameraBtn = document.getElementById("openCameraBtn");
if(openCameraBtn){
    openCameraBtn.addEventListener("click", function(){
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if(isMobile){
            cameraInput.click();
        } else {
            startCamera();
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
    croppedImageBlob = null;
    originalImageSource = "";
    hidePreview();
    if(cropEditor){
        cropEditor.style.display = "none";
    }
    fileInput.value = "";

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Camera API is not supported in your browser. Please use the file upload option.");
        return;
    }

    if (!window.isSecureContext && window.location.protocol !== "https:") {
        alert("Camera requires HTTPS. Please access the site over HTTPS or use the file upload option.");
        return;
    }

    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
        .then(stream => {
            cameraStream             = stream;
            video.srcObject          = stream;
            video.style.display      = "block";
            captureBtn.style.display = "inline-block";
        })
        .catch(err => {
            console.error("Camera error:", err);
            if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
                alert("Camera access denied. Please allow camera permissions and try again.");
            } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
                alert("No camera found on this device.");
            } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
                alert("Camera is already in use by another application.");
            } else if (err.name === "OverconstrainedError") {
                alert("Camera does not meet the required constraints.");
            } else if (err.name === "TypeError") {
                alert("Camera requires HTTPS. Please access via HTTPS or use file upload.");
            } else {
                alert("Unable to access camera: " + err.message);
            }
        });
}

function captureImage() {
    const video   = document.getElementById("camera");

    const canvas = document.createElement("canvas");
    const ctx    = canvas.getContext("2d");

    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0);

    const imageData = canvas.toDataURL("image/png");
    originalImageSource = imageData;
    initializeCropper(imageData);

    // save as Blob so analyzeImage() can upload it
    canvas.toBlob(blob => {
        capturedBlob = blob;
        cameraFile = null;
        croppedImageBlob = null;
    }, "image/png");

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }

    video.style.display = "none";
    document.getElementById("captureBtn").style.display = "none";
}

function beginCropDrag(clientX, clientY, pointerId = null) {
    if(!cropViewport || !cropState.naturalWidth){
        return;
    }

    cropState.dragging = true;
    cropState.pointerId = pointerId;
    cropState.startX = clientX;
    cropState.startY = clientY;
    cropState.startLeft = cropState.left;
    cropState.startTop = cropState.top;
    cropViewport.classList.add("dragging");
}

function moveCropDrag(clientX, clientY) {
    if(!cropState.dragging){
        return;
    }

    cropState.left = cropState.startLeft + (clientX - cropState.startX);
    cropState.top = cropState.startTop + (clientY - cropState.startY);
    renderCropImage();
}

function endCropDrag() {
    cropState.dragging = false;
    cropState.pointerId = null;
    if(cropViewport){
        cropViewport.classList.remove("dragging");
    }
}

if(cropViewport){
    cropViewport.addEventListener("pointerdown", function(e){
        if(!cropState.naturalWidth){
            return;
        }

        beginCropDrag(e.clientX, e.clientY, e.pointerId);
        cropViewport.setPointerCapture(e.pointerId);
    });

    cropViewport.addEventListener("pointermove", function(e){
        if(cropState.pointerId !== e.pointerId){
            return;
        }

        moveCropDrag(e.clientX, e.clientY);
    });

    cropViewport.addEventListener("pointerup", endCropDrag);
    cropViewport.addEventListener("pointercancel", endCropDrag);
    cropViewport.addEventListener("lostpointercapture", endCropDrag);
}

if(cropZoom){
    cropZoom.addEventListener("input", function(){
        syncCropZoom(this.value);
    });
}

if(resetCropBtn){
    resetCropBtn.addEventListener("click", function(){
        if(cropZoom){
            cropZoom.value = "1";
        }

        croppedImageBlob = null;

        if(originalImageSource){
            initializeCropper(originalImageSource);
            return;
        }

        syncCropZoom(1);
        resetCropPosition();
    });
}

if(applyCropBtn){
    applyCropBtn.addEventListener("click", function(){
        if(!cropViewport || !cropImage || !cropState.naturalWidth || !cropState.naturalHeight){
            return;
        }

        const frameLeft = cropFrame ? cropFrame.offsetLeft : 0;
        const frameTop = cropFrame ? cropFrame.offsetTop : 0;
        const frameWidth = cropFrame ? cropFrame.clientWidth : cropViewport.clientWidth;
        const frameHeight = cropFrame ? cropFrame.clientHeight : cropViewport.clientHeight;
        const sourceX = Math.max(0, (frameLeft - cropState.left) / cropState.scale);
        const sourceY = Math.max(0, (frameTop - cropState.top) / cropState.scale);
        const sourceWidth = Math.min(cropState.naturalWidth - sourceX, frameWidth / cropState.scale);
        const sourceHeight = Math.min(cropState.naturalHeight - sourceY, frameHeight / cropState.scale);
        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");

        canvas.width = 512;
        canvas.height = 512;
        context.fillStyle = "#f7fbf8";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(
            cropImage,
            sourceX,
            sourceY,
            sourceWidth,
            sourceHeight,
            0,
            0,
            canvas.width,
            canvas.height,
        );

        canvas.toBlob(blob => {
            croppedImageBlob = blob;
        }, "image/jpeg", 0.92);
    });
}

window.addEventListener("resize", function(){
    if(cropEditor && cropEditor.style.display === "flex" && cropState.naturalWidth){
        cropState.minScale = getBaseCropScale();
        cropState.scale = cropState.minScale * Number(cropZoom.value || 1);
        resetCropPosition();
    }
});


// analysis — POST to Django /analyze/
async function analyzeImage() {
    const fileInput = document.getElementById("fileInput");
    const preview   = document.getElementById("preview");
    const hasImageSource =
        !!croppedImageBlob ||
        !!capturedBlob ||
        !!cameraFile ||
        !!originalImageSource ||
        fileInput.files.length > 0 ||
        preview.style.display !== "none";

    if (!hasImageSource) {
        alert("Please upload or capture an image first.");
        return;
    }

    let existingResultSection = document.querySelector(".result-section");
    if (existingResultSection) existingResultSection.remove();

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
    if(croppedImageBlob){
        formData.append("image", croppedImageBlob, "cropped_leaf.jpg");
    } else if(fileInput.files.length){
        formData.append("image", fileInput.files[0]);
    } else if(cameraFile){
        formData.append("image", cameraFile, "camera_capture.jpg");
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
                `;
            } else if(data.status === "error"){
                const errorMsg = data.error ? `<p style="color:red;"><small>Analysis failed: ${data.error}</small></p>` : '';
                resultBox.innerHTML = `
                    <h3>Analysis Failed</h3>
                    <p>Unable to process image.</p>
                    <p><b>Reason:</b> ${data.leaf_label || 'Leaf model unavailable'}</p>
                    ${errorMsg}
                `;
            } else if(data.is_leaf === false || data.disease_name === "Not a leaf") {
                const errorMsg = data.leaf_error ? `<p style="color:orange;"><small>${data.leaf_error}</small></p>` : '';
                resultBox.innerHTML = `
                    <h3>Object detected: Not a leaf</h3>
                    <p>Please upload an image of a plant leaf.</p>
                    <p><b>Leaf model decision:</b> ${data.leaf_label || 'N/A'} (${data.leaf_confidence ? (data.leaf_confidence * 100).toFixed(1) + '%' : 'N/A'})</p>
                    ${errorMsg}
                `;
            } else {
                const rec = data.recommendation || {};
                const isHealthy = data.disease_name.toLowerCase().includes('healthy');
                const displayName = isHealthy ? data.disease_name.replace(/___healthy/gi, '') : data.disease_name;
                resultBox.innerHTML = `
                    <h3>${isHealthy ? '' : 'Disease: '}${displayName}</h3>
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
