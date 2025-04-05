let voiceProfiles = {};

const STORIES_PER_PAGE = 20;
let currentPage = 1;
let totalStories = 0;
let isContinuousReading = false;
let audioEndedHandler = null;

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
    
    // Add animation class to story cards
    animateStoryCards();
    
    // Initialize placeholder text
    initializePlaceholder();
});

// Function to animate story cards with staggered delay
function animateStoryCards() {
    const storyCards = document.querySelectorAll('.story-card');
    storyCards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 * index);
    });
}

// Function to initialize placeholder text
function initializePlaceholder() {
    const storyOutput = document.getElementById('storyOutput');
    const placeholder = storyOutput.querySelector('.story-placeholder');
    
    if (placeholder && !storyOutput.textContent.trim()) {
        placeholder.style.display = 'block';
    } else if (placeholder) {
        placeholder.style.display = 'none';
    }
}

// Function to randomly select and read a story from saved stories
async function readRandomStory(startContinuous = false) {
    try {
        if (startContinuous) {
            isContinuousReading = true;
            document.getElementById('randomReadBtn').style.display = 'none';
            document.getElementById('stopReadBtn').style.display = 'inline-flex';
        }
        
        // Show loading indicator in story output
        const storyOutput = document.getElementById('storyOutput');
        storyOutput.innerHTML = `
            <div class="loading-indicator">
                <div class="loading"><div></div><div></div><div></div><div></div></div>
                <p>Loading a random story...</p>
            </div>
        `;
        
        // Fetch all stories
        const response = await fetch('/stories');
        const data = await response.json();
        const stories = data.stories;
        
        if (stories.length === 0) {
            storyOutput.innerHTML = `<div class="error-message">No saved stories found. Generate a story first!</div>`;
            stopContinuousReading();
            return;
        }
        
        // Select a random story
        const randomIndex = Math.floor(Math.random() * stories.length);
        const randomStory = stories[randomIndex];
        
        // Fetch the full story content using the story ID
        const storyResponse = await fetch(`/stories/${randomStory.id}`);
        const storyData = await storyResponse.json();
        
        if (!storyData.story) {
            throw new Error('Failed to load the full story content');
        }
        
        // Display the story in the story output area
        storyOutput.textContent = storyData.story;
        document.getElementById('language').value = storyData.language || 'zh'; // Default to Chinese if not specified
        document.getElementById('readBtn').disabled = false;
        
        // Stream audio for the random story
        const audioPlayer = document.getElementById('audioPlayer');
        
        // Remove any existing ended event listener
        if (audioEndedHandler) {
            audioPlayer.removeEventListener('ended', audioEndedHandler);
            audioEndedHandler = null;
        }
        
        // Add event listener for continuous reading
        if (isContinuousReading) {
            audioEndedHandler = function() {
                if (isContinuousReading) {
                    // Start reading the next random story when current one ends
                    setTimeout(() => readRandomStory(), 1500); // Small delay between stories
                }
            };
            audioPlayer.addEventListener('ended', audioEndedHandler);
        }
        
        await streamAudio(storyData.story, storyData.language || 'zh');
    } catch (error) {
        console.error('Error reading random story:', error);
        document.getElementById('storyOutput').innerHTML = `<div class="error-message">Failed to read a random story. Please try again.</div>`;
        stopContinuousReading();
    }
}

// Function to stop continuous reading
function stopContinuousReading() {
    isContinuousReading = false;
    document.getElementById('randomReadBtn').style.display = 'inline-flex';
    document.getElementById('stopReadBtn').style.display = 'none';
    
    // Remove the ended event listener but don't stop current playback
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioEndedHandler) {
        audioPlayer.removeEventListener('ended', audioEndedHandler);
        audioEndedHandler = null;
    }
}

// Function to load and display stories
async function loadStories(page = 1) {
    try {
        // Show loading indicator
        const container = document.getElementById('savedStories');
        container.innerHTML = `
            <div class="loading-indicator">
                <div class="loading"><div></div><div></div><div></div><div></div></div>
                <p>Loading your stories...</p>
            </div>
        `;
        
        const response = await fetch('/stories');
        const data = await response.json();
        const stories = data.stories;
        totalStories = stories.length;
        
        // Calculate pagination
        const totalPages = Math.ceil(totalStories / STORIES_PER_PAGE);
        const startIndex = (page - 1) * STORIES_PER_PAGE;
        const endIndex = Math.min(startIndex + STORIES_PER_PAGE, totalStories);
        const pageStories = stories.slice(startIndex, endIndex);
        
        // Clear container after loading
        container.innerHTML = '';
        
        // If no stories, show message
        if (pageStories.length === 0) {
            container.innerHTML = `<div class="no-stories">No stories saved yet. Generate your first story!</div>`;
            return;
        }
        
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
                        <button class="download-audio-btn" data-id="${story.id}"><i class="fas fa-download"></i> Download</button>
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

    // Add event listeners for download buttons
    document.querySelectorAll('.download-audio-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const storyId = btn.dataset.id;
            try {
                // Show loading state
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
                btn.disabled = true;
                
                // Get the story data to pass to the download endpoint
                const storyResponse = await fetch(`/stories/${storyId}`);
                const storyData = await storyResponse.json();
                
                if (!storyData.story) {
                    throw new Error('Failed to load story content');
                }
                
                // Get the current TTS service and language
                const ttsService = document.getElementById('tts-service').value;
                const language = storyData.language || 'zh';
                
                // Create a download link
                const downloadLink = document.createElement('a');
                downloadLink.href = `/download_audio?story_id=${storyId}&tts_service=${ttsService}`;
                downloadLink.download = `story_${storyId}.mp3`;
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
                
                // Reset button state
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }, 1000);
            } catch (error) {
                console.error('Error downloading audio:', error);
                alert('Failed to download audio. Please try again.');
                btn.innerHTML = '<i class="fas fa-download"></i> Download';
                btn.disabled = false;
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
        alert('Please enter a theme for the story');
        return;
    }

    try {
        // Show loading animation in story output
        storyOutput.innerHTML = `
            <div class="loading-indicator">
                <div class="loading"><div></div><div></div><div></div><div></div></div>
                <p>Creating your magical story...</p>
            </div>
        `;
        
        // Disable generate button during generation
        const originalBtnText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        generateBtn.disabled = true;
        
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
                    storyOutput.classList.add('story-fade-in');
                }
                
                if (data.done) {
                    eventSource.close();
                    readBtn.disabled = false;
                    generateBtn.innerHTML = originalBtnText;
                    generateBtn.disabled = false;
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
            storyOutput.innerHTML = `<div class="error-message">Error generating story. Please try again.</div>`;
            generateBtn.innerHTML = originalBtnText;
            generateBtn.disabled = false;
        };

    } catch (error) {
        console.error('Error:', error);
        storyOutput.innerHTML = `<div class="error-message">An error occurred while generating the story</div>`;
        generateBtn.innerHTML = originalBtnText;
        generateBtn.disabled = false;
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

        // Set a timeout to handle stalled connections
        let stallTimeout;
        const resetStallTimeout = () => {
            if (stallTimeout) clearTimeout(stallTimeout);
            stallTimeout = setTimeout(() => {
                console.log('Audio stream stalled, waiting for more data...');
                // We don't end the stream here, just log the stall
            }, 5000); // 5 seconds timeout
        };

        // Handle audio player events
        audioPlayer.addEventListener('playing', resetStallTimeout, { once: false });
        audioPlayer.addEventListener('waiting', resetStallTimeout, { once: false });
        
        mediaSource.addEventListener('sourceopen', async () => {
            const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
            sourceBuffer.mode = 'sequence';

            const reader = response.body.getReader();
            let done = false;
            let hasStartedPlaying = false;

            // Start the stall detection
            resetStallTimeout();

            // Process chunks as they arrive
            while (!done) {
                try {
                    const { value, done: readerDone } = await reader.read();
                    
                    // Clear the stall timeout since we received data
                    resetStallTimeout();
                    
                    if (value && value.byteLength > 0) {
                        // Wait if the buffer is currently updating
                        if (sourceBuffer.updating) {
                            await new Promise(resolve => {
                                sourceBuffer.addEventListener('updateend', resolve, { once: true });
                            });
                        }
                        
                        // Append the new chunk to the buffer
                        sourceBuffer.appendBuffer(value);
                        
                        // Start playback if it hasn't started and we have some data
                        if (!hasStartedPlaying && !audioPlayer.paused) {
                            hasStartedPlaying = true;
                        } else if (hasStartedPlaying && audioPlayer.paused) {
                            // Try to resume if paused but we have more data
                            audioPlayer.play().catch(e => console.warn('Could not resume playback:', e));
                        }
                    }
                    
                    done = readerDone;
                } catch (error) {
                    console.warn('Error while reading stream chunk:', error);
                    // Don't terminate the stream on chunk errors, try to continue
                    if (error.name !== 'AbortError') {
                        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait a bit before retrying
                    } else {
                        done = true; // Stop on abort
                    }
                }
            }

            // Clean up the stall timeout
            if (stallTimeout) clearTimeout(stallTimeout);

            // End the stream properly when done
            sourceBuffer.addEventListener('updateend', () => {
                if (done && !sourceBuffer.updating) {
                    try {
                        mediaSource.endOfStream();
                    } catch (e) {
                        console.warn('Error ending media stream:', e);
                    }
                }
            });
        });

        await audioPlayer.play().catch(e => {
            console.warn('Initial playback failed, will retry when data arrives:', e);
        });
    } catch (error) {
        console.error('Error streaming audio:', error);
    }
}

document.getElementById('readBtn').addEventListener('click', async () => {
    const story = document.getElementById('storyOutput').textContent;
    const language = document.getElementById('language').value;
    await streamAudio(story, language);
});

// Add event listeners for random read and stop buttons
document.getElementById('randomReadBtn').addEventListener('click', () => readRandomStory(true));
document.getElementById('stopReadBtn').addEventListener('click', stopContinuousReading);
