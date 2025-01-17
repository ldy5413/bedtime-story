let voiceProfiles = {};

const STORIES_PER_PAGE = 20;
let currentPage = 1;
let totalStories = 0;

async function loadTTSOptions() {
    try {
        const response = await fetch('/tts-options');
        const data = await response.json();
        voiceProfiles = data.voices;
        updateVoiceOptions();
    } catch (error) {
        console.error('Error loading TTS options:', error);
    }
}

function updateVoiceOptions() {
    const language = document.getElementById('language').value;
    const ttsService = document.getElementById('tts-service').value;
    const voiceSelect = document.getElementById('voice-profile');
    
    // Clear existing options
    voiceSelect.innerHTML = '<option value="">Default</option>';
    
    // Only show voice profiles for F5 TTS
    if (ttsService === 'f5tts' && voiceProfiles && voiceProfiles.length > 0) {
        // Filter profiles by selected language
        const languageProfiles = voiceProfiles.filter(profile => profile.language === language);
        
        languageProfiles.forEach(profile => {
            const option = document.createElement('option');
            option.value = profile.id;
            option.textContent = profile.name;
            voiceSelect.appendChild(option);
        });
        voiceSelect.style.display = 'inline';
    } else {
        voiceSelect.style.display = 'none';
    }
}

// Add event listeners for language and tts-service changes
document.getElementById('language').addEventListener('change', updateVoiceOptions);
document.getElementById('tts-service').addEventListener('change', updateVoiceOptions);

// Load TTS options when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadTTSOptions();
    loadStories();
});

// Function to load and display stories
async function loadStories(page = 1) {
    try {
        const response = await fetch('/stories');
        const data = await response.json();
        const stories = data.stories;
        totalStories = stories.length;
        
        // Calculate pagination
        const totalPages = Math.ceil(totalStories / STORIES_PER_PAGE);
        const startIndex = (page - 1) * STORIES_PER_PAGE;
        const endIndex = Math.min(startIndex + STORIES_PER_PAGE, totalStories);
        const pageStories = stories.slice(startIndex, endIndex);
        
        const container = document.getElementById('savedStories');
        
        // Clear container
        container.innerHTML = '';
        
        // Add stories for current page
        if (pageStories.length > 0) {
            // Add stories
            pageStories.forEach(story => {
                const storyCard = document.createElement('div');
                storyCard.className = 'story-card';
                storyCard.innerHTML = `
                    <div class="story-card-header">
                        <h3>${story.theme}</h3>
                        <button class="favorite-btn ${story.favorite ? 'favorited' : ''}" data-id="${story.id}">
                            ${story.favorite ? '★' : '☆'}
                        </button>
                    </div>
                    <p class="story-preview">${story.preview}...</p>
                    <div class="story-actions">
                        <button class="read-story-btn" data-id="${story.id}">Read</button>
                        <button class="delete-story-btn" data-id="${story.id}">Delete</button>
                    </div>
                `;
                container.appendChild(storyCard);
            });

            // Add pagination controls
            const paginationDiv = document.createElement('div');
            paginationDiv.className = 'pagination';
            paginationDiv.innerHTML = createPaginationControls(page, totalPages);
            container.appendChild(paginationDiv);

            // Add event listeners for read and delete buttons
            addStoryButtonListeners();
        } else {
            container.innerHTML = '<p>No stories saved yet.</p>';
        }
    } catch (error) {
        console.error('Error loading stories:', error);
    }
}

function createPaginationControls(currentPage, totalPages) {
    let controls = '<div class="pagination-controls">';
    
    // Previous button
    if (currentPage > 1) {
        controls += `<button onclick="loadStories(${currentPage - 1})">Previous</button>`;
    }
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPage) {
            controls += `<button class="current-page" disabled>${i}</button>`;
        } else {
            controls += `<button onclick="loadStories(${i})">${i}</button>`;
        }
    }
    
    // Next button
    if (currentPage < totalPages) {
        controls += `<button onclick="loadStories(${currentPage + 1})">Next</button>`;
    }
    
    controls += '</div>';
    return controls;
}

function addStoryButtonListeners() {
    // Add event listeners for read buttons
    document.querySelectorAll('.read-story-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const storyId = btn.dataset.id;
            try {
                const response = await fetch(`/stories/${storyId}`);
                const data = await response.json();
                document.getElementById('storyOutput').textContent = data.story;
                document.getElementById('language').value = data.language;
                document.getElementById('readBtn').disabled = false;
            } catch (error) {
                console.error('Error loading story:', error);
            }
        });
    });

    // Add event listeners for delete buttons
    document.querySelectorAll('.delete-story-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to delete this story?')) {
                try {
                    const response = await fetch(`/stories/${btn.dataset.id}`, {
                        method: 'DELETE'
                    });
                    if (response.ok) {
                        // Reload current page after deletion
                        loadStories(currentPage);
                    }
                } catch (error) {
                    console.error('Error deleting story:', error);
                }
            }
        });
    });

    // Add event listeners for favorite buttons
    document.querySelectorAll('.favorite-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const storyId = btn.dataset.id;
            const isFavorited = btn.classList.contains('favorited');
            try {
                const response = await fetch(`/stories/${storyId}/favorite`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ favorite: !isFavorited })
                });
                if (response.ok) {
                    btn.classList.toggle('favorited');
                    btn.textContent = btn.classList.contains('favorited') ? '★' : '☆';
                }
            } catch (error) {
                console.error('Error updating favorite status:', error);
            }
        });
    });
}

// Handle click on read story buttons for saved stories
document.addEventListener('click', async (e) => {
    if (e.target.classList.contains('read-story-btn')) {
        const storyId = e.target.dataset.id;
        try {
            const response = await fetch(`/stories/${storyId}`);
            const data = await response.json();

            if (data.story) {
                await streamAudio(data.story, data.language);
                // document.getElementById('storyOutput').textContent = data.story;

                // // Stream audio
                // const audioPlayer = document.getElementById('audioPlayer');
                // const responseStream = await fetch('/stream_audio', {
                //     method: 'POST',
                //     headers: { 'Content-Type': 'application/json' },
                //     body: JSON.stringify({
                //         story: data.story,
                //         language: data.language,
                //     }),
                // });

                // const reader = responseStream.body.getReader();
                // const mediaSource = new MediaSource();
                // audioPlayer.src = URL.createObjectURL(mediaSource);

                // mediaSource.addEventListener('sourceopen', async () => {
                //     const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
                //     sourceBuffer.mode = 'sequence'; // Avoid overlapping issues
                //     let done = false;

                //     while (!done) {
                //         const { value, done: readerDone } = await reader.read();
                //         if (value) {
                //             if (sourceBuffer.updating) {
                //                 // Wait until the buffer is ready for new data
                //                 await new Promise(resolve => {
                //                     sourceBuffer.addEventListener('updateend', resolve, { once: true });
                //                 });
                //             }
                //             sourceBuffer.appendBuffer(value);
                //         }
                //         done = readerDone;
                //     }

                //     // End the stream once all chunks are appended
                //     sourceBuffer.addEventListener('updateend', () => {
                //         if (done) {
                //             mediaSource.endOfStream();
                //         }
                //     });
                // });

                // audioPlayer.play();
            }
        } catch (error) {
            console.error('Error loading story:', error);
        }
    }
});


// Add warning modal to HTML
const modalHTML = `
    <div id="warningModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);">
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 5px; text-align: center;">
            <p id="warningMessage"></p>
            <button onclick="document.getElementById('warningModal').style.display = 'none'">OK</button>
        </div>
    </div>
`;
document.body.insertAdjacentHTML('beforeend', modalHTML);

async function generateStory() {
    const theme = document.getElementById('theme').value;
    const language = document.getElementById('language').value;
    const generateBtn = document.getElementById('generateBtn');
    const readBtn = document.getElementById('readBtn');
    const storyOutput = document.getElementById('storyOutput');

    if (!theme) {
        alert('Please enter a theme');
        return;
    }

    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';
    storyOutput.textContent = 'Generating story...';

    try {
        // Create EventSource for server-sent events
        const eventSource = new EventSource(`/generate?theme=${encodeURIComponent(theme)}&language=${encodeURIComponent(language)}`);
        let story = '';

        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                if (data.chunk) {
                    story += data.chunk;
                    storyOutput.textContent = story;
                }
                
                if (data.done) {
                    eventSource.close();
                    readBtn.disabled = false;
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate Story';
                }
            } catch (e) {
                console.error('Error parsing SSE data:', e);
                eventSource.close();
                throw e;
            }
        };

        eventSource.onerror = function(error) {
            console.error('EventSource error:', error);
            eventSource.close();
            storyOutput.textContent = 'Error generating story. Please try again.';
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Story';
        };

    } catch (error) {
        console.error('Error:', error);
        storyOutput.textContent = 'Error generating story. Please try again.';
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Story';
    }
}

// Add event listener for generate button
document.getElementById('generateBtn').addEventListener('click', generateStory);

async function streamAudio(story, language) {
    const ttsService = document.getElementById('tts-service').value;
    const voiceProfileSelect = document.getElementById('voice-profile');
    const voiceProfile = voiceProfileSelect.value ? JSON.parse(voiceProfileSelect.value) : null;
    
    const audioPlayer = document.getElementById('audioPlayer');
    
    try {
        const response = await fetch('/stream_audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                story: story,
                language: language,
                tts_service: ttsService,
                voice_profile: voiceProfile
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Use MediaSource for both services since they're both MP3 now
        const mediaSource = new MediaSource();
        audioPlayer.src = URL.createObjectURL(mediaSource);

        mediaSource.addEventListener('sourceopen', async () => {
            const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
            sourceBuffer.mode = 'sequence';

            const reader = response.body.getReader();
            let done = false;

            while (!done) {
                const { value, done: readerDone } = await reader.read();
                if (value) {
                    if (sourceBuffer.updating) {
                        await new Promise(resolve => {
                            sourceBuffer.addEventListener('updateend', resolve, { once: true });
                        });
                    }
                    sourceBuffer.appendBuffer(value);
                }
                done = readerDone;
            }

            sourceBuffer.addEventListener('updateend', () => {
                if (done && !sourceBuffer.updating) {
                    mediaSource.endOfStream();
                }
            });
        });

        await audioPlayer.play();
    } catch (error) {
        console.error('Error streaming audio:', error);
    }
}

document.getElementById('readBtn').addEventListener('click', async () => {
    const story = document.getElementById('storyOutput').textContent;
    const language = document.getElementById('language').value;
    await streamAudio(story, language);
});
