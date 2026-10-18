document.addEventListener('DOMContentLoaded', () => {
    // Existing elements...
    const workspaceList = document.getElementById('workspace-list');
    const loadingEl = document.getElementById('workspace-loading');
    const workspaceView = document.getElementById('workspace-view');
    const workspaceNameEl = document.getElementById('workspace-name');
    const createBtn = document.getElementById('create-workspace-btn');
    const docList = document.getElementById('document-list');
    
    // Chat elements
    const newChatBtn = document.getElementById('new-chat-btn');
    const conversationList = document.getElementById('conversation-list');
    const chatWindow = document.getElementById('chat-window');
    const messageHistory = document.getElementById('message-history');
    const chatInput = document.getElementById('chat-input');
    const sendChatBtn = document.getElementById('send-chat-btn');

    let selectedWorkspace = null;
    let selectedConversation = null;

    // ... (Existing workspace/doc functions stay the same)
    
    async function fetchConversations() {
        if (!selectedWorkspace) return;
        const res = await fetch(`/api/v1/workspaces/${selectedWorkspace.id}/conversations`);
        if (!res.ok) return;
        const convs = await res.json();
        conversationList.innerHTML = '';
        convs.forEach(c => {
            const btn = document.createElement('button');
            btn.className = 'btn';
            btn.textContent = c.title || 'Untitled Chat';
            btn.onclick = () => selectConversation(c);
            conversationList.appendChild(btn);
        });
    }

    async function selectConversation(conv) {
        selectedConversation = conv;
        chatWindow.classList.remove('hidden');
        document.getElementById('chat-title').textContent = conv.title;
        loadMessages();
    }

    async function loadMessages() {
        const res = await fetch(`/api/v1/conversations/${selectedConversation.id}/messages`);
        if (!res.ok) return;
        const msgs = await res.json();
        messageHistory.innerHTML = '';
        msgs.forEach(m => {
            const div = document.createElement('div');
            div.className = `message ${m.sender_role}`;
            div.textContent = m.text;
            messageHistory.appendChild(div);
        });
        messageHistory.scrollTop = messageHistory.scrollHeight;
    }

    sendChatBtn.onclick = async () => {
        const text = chatInput.value.trim();
        if (!text || !selectedConversation) return;
        chatInput.value = '';
        
        try {
            const res = await fetch(`/api/v1/conversations/${selectedConversation.id}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text })
            });
            if (!res.ok) throw new Error('Chat failed');
            loadMessages();
        } catch (e) { alert('Chat failed: ' + e.message); }
    };

    newChatBtn.onclick = async () => {
        const title = prompt('Chat title:');
        const res = await fetch(`/api/v1/workspaces/${selectedWorkspace.id}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });
        if (res.ok) fetchConversations();
    };

    // --- (Keeping existing Workspace/Doc functions unchanged below) ---
    // ... existing fetchWorkspaces, renderWorkspaceList, selectWorkspace, fetchDocuments, renderDocuments, startPolling, stopPolling, deleteDocument, uploadBtn.onclick, createBtn.onclick ...
    
    // Merge existing functions from Stage 2/3 here
    // [Truncated for brevity in representation - would contain all existing functions]
});