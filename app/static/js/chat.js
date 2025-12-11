function fetchNewMessages() {
    fetch(window.location.pathname + "/messages?last_id=" + window.lastMessageId)
        .then(res => res.json())
        .then(messages => {

            if (messages.length === 0) return;

            const chatWindow = document.getElementById("chat-window");

            messages.forEach(msg => {

                // Update last ID
                window.lastMessageId = msg.id;

                // Create message bubble
                const div = document.createElement("div");
                div.classList.add("chat-message");
                div.classList.add(msg.sender === window.currentUser ? "me" : "other");
                div.dataset.id = msg.id;

                div.innerHTML = `
                    <div class="sender">${msg.sender}</div>
                    <div class="bubble">${msg.content}</div>
                    <div class="timestamp">${msg.timestamp}</div>
                `;

                chatWindow.appendChild(div);
            });

            chatWindow.scrollTop = chatWindow.scrollHeight;
        });
}

// Poll every 1.5 seconds
setInterval(fetchNewMessages, 1500);
