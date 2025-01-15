let mediaRecorder;
let audioChunks = [];

function toggleInputMethod() {
    const method = document.getElementById('input-method').value;
    document.getElementById('upload-section').style.display = method === 'upload' ? 'block' : 'none';
    document.getElementById('record-section').style.display = method === 'record' ? 'block' : 'none';
}

async function startRecording() {
    audioChunks = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
    };
    
    mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        document.getElementById('recordingPreview').src = audioUrl;
        document.getElementById('recordingPreview').style.display = 'block';
        
        // Convert blob to base64 for form submission
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = () => {
            document.getElementById('recorded-audio-data').value = reader.result;
        };
    };
    
    mediaRecorder.start();
    document.querySelector('button[onclick="startRecording"]').disabled = true;
    document.querySelector('button[onclick="stopRecording"]').disabled = false;
}

function stopRecording() {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
    document.querySelector('button[onclick="startRecording"]').disabled = false;
    document.querySelector('button[onclick="stopRecording"]').disabled = true;
} 