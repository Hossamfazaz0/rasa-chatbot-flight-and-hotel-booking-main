// Configuration
const CONFIG = {
    RASA_URL: 'http://localhost:5005/webhooks/rest/webhook',
    USER_ID: 'user_' + Math.random().toString(36).substr(2, 9),
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000,
    WELCOME_MESSAGE: `مرحباً بك في وكالة السفر الذكية! 🌟<br>
كيف يمكنني مساعدتك اليوم؟<br><br>
يمكنني مساعدتك في:
<ul>
    <li>✈️ حجز رحلات طيران</li>
    <li>🏨 حجز فنادق</li>
    <li>🗺️ تخطيط رحلتك</li>
</ul>`
};

// DOM Elements
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const messagesContainer = document.getElementById('messagesContainer');
const quickActionsContainer = document.getElementById('quickActionsContainer'); // For dynamic buttons
const welcomeTimeElement = document.getElementById('welcomeTime');

// State
let retryCount = 0;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    setupEventListeners();
});

// Initialize chat
function initializeChat() {
    messageInput.focus();
    setWelcomeTime();
    // loadChatHistory(); // Load history, which might include the welcome message or add it if history is empty
    if (messagesContainer.children.length === 0) { // If no history, add welcome
        addMessage(CONFIG.WELCOME_MESSAGE, 'bot', false); // Don't save initial welcome to history again if loading
    }
}

// Setup event listeners
function setupEventListeners() {
    sendButton.addEventListener('click', handleSendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px'; // Auto-resize textarea
    });
}

// Handle send message
async function handleSendMessage() {
    const messageText = messageInput.value.trim();
    if (!messageText) return;

    setInputState(false);
    addMessage(messageText, 'user');
    messageInput.value = '';
    messageInput.style.height = 'auto'; // Reset height

    try {
        const rasaResponse = await sendToRasa(messageText);
        handleRasaResponse(rasaResponse);
        retryCount = 0;
    } catch (error) {
        console.error('Error sending message:', error);
        handleError(error, messageText);
    }

    setInputState(true);
    messageInput.focus();
}

// Send message to Rasa
async function sendToRasa(message) {
    const payload = { sender: CONFIG.USER_ID, message: message };
    try {
        const response = await fetch(CONFIG.RASA_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

// Handle Rasa response
function handleRasaResponse(responses) {
    clearQuickActions(); // Clear previous buttons

    if (!responses || responses.length === 0) {
        addMessage('عذراً، لم أتمكن من فهم طلبك. يرجى المحاولة مرة أخرى.', 'bot');
        return;
    }

    responses.forEach((response, index) => {
        setTimeout(() => {
            if (response.text) {
                addMessage(response.text, 'bot');
            }
            if (response.buttons && response.buttons.length > 0) {
                addQuickActionButtons(response.buttons);
            }
            // Note: Attachments are not handled in this simplified version
        }, index * 300); // Stagger responses slightly
    });
}

// Add message to chat
function addMessage(text, sender, save = true) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.innerHTML = formatMessageText(text); // Use a dedicated formatter

    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = getCurrentTime();

    contentDiv.appendChild(textDiv);
    contentDiv.appendChild(timeDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    scrollToBottom();
    if (save) {
        // saveChatHistory();
    }
    
    // Simple animation
    setTimeout(() => messageDiv.style.opacity = 1, 50);
}

// Format message text (links, newlines)
function formatMessageText(text) {
    text = text.replace(/\n/g, '<br>');
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}

// Add quick action buttons
function addQuickActionButtons(buttons) {
    buttons.forEach(buttonInfo => {
        const button = document.createElement('button');
        button.className = 'quick-btn';
        button.textContent = buttonInfo.title;
        button.onclick = () => {
            sendQuickMessage(buttonInfo.payload);
            clearQuickActions(); // Remove buttons after click
        };
        quickActionsContainer.appendChild(button);
    });
    if (buttons.length > 0) {
        quickActionsContainer.style.display = 'flex';
         scrollToBottom(); // Ensure buttons are visible
    }
}

// Clear quick action buttons
function clearQuickActions() {
    quickActionsContainer.innerHTML = '';
    quickActionsContainer.style.display = 'none';
}

// Send a message via quick action
function sendQuickMessage(payload) {
    addMessage(payload, 'user'); // Display what the user "clicked"
    
    setInputState(false); // Disable input while processing
    
    sendToRasa(payload)
        .then(rasaResponse => {
            handleRasaResponse(rasaResponse);
            retryCount = 0;
        })
        .catch(error => {
            console.error('Error sending quick message:', error);
            handleError(error, payload);
        })
        .finally(() => {
            setInputState(true);
            messageInput.focus();
        });
}

// Set input state (enabled/disabled)
function setInputState(enabled) {
    messageInput.disabled = !enabled;
    sendButton.disabled = !enabled;
    if (enabled) {
        messageInput.focus();
    }
}

// Handle errors with retry
function handleError(error, originalMessage) {
    let errorMessage = 'عذراً، حدث خطأ في الاتصال. ';
    if (retryCount < CONFIG.MAX_RETRIES) {
        retryCount++;
        errorMessage += `جاري المحاولة مرة أخرى... (${retryCount}/${CONFIG.MAX_RETRIES})`;
        addMessage(errorMessage, 'bot');
        setTimeout(async () => {
            try {
                const rasaResponse = await sendToRasa(originalMessage);
                handleRasaResponse(rasaResponse);
            } catch (e) {
                handleError(e, originalMessage);
            }
        }, CONFIG.RETRY_DELAY);
    } else {
        errorMessage += 'يرجى التحقق من الاتصال والمحاولة لاحقاً.';
        addMessage(errorMessage, 'bot');
        retryCount = 0; // Reset for future messages
    }
}

// Scroll to bottom of messages
function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Get current time formatted
function getCurrentTime() {
    return new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit', hour12: true });
}

// Set welcome message time
function setWelcomeTime() {
    if (welcomeTimeElement) {
        welcomeTimeElement.textContent = getCurrentTime();
    }
}

// Save chat history to localStorage
// function saveChatHistory() {
//     const messages = Array.from(messagesContainer.children)
//         .filter(msg => !msg.querySelector('#welcomeTime')) // Don't re-save the initial welcome structure if it's static
//         .map(msg => ({
//             sender: msg.classList.contains('user-message') ? 'user' : 'bot',