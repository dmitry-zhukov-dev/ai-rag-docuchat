document.addEventListener('DOMContentLoaded', () => {
    const state = {
        context: null, documents: [], chatSubmitting: false,
        uploading: false, loadingDocuments: false, pollTimer: null,
    };
    const $ = (id) => document.getElementById(id);
    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }
    function showToast(message) {
        $('app-error').textContent = message;
        $('app-error').classList.remove('hidden');
    }
    function updateControls() {
        const ready = state.context && !state.uploading && !state.chatSubmitting &&
            state.documents.some((doc) => doc.indexing_status === 'completed') &&
            !state.documents.some((doc) => doc.indexing_status === 'processing');
        $('chat-input').disabled = !ready;
        $('send-chat-btn').disabled = !ready;
        $('chat-input').placeholder = ready ? 'Ask a question about your documents…' : 'Waiting for a ready document…';
        $('upload-area').disabled = !state.context || state.uploading;
    }
    async function api(path, options = {}) {
        const response = await fetch(path, {
            credentials: 'same-origin',
            ...options,
            headers: options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
        });
        if (response.status === 401) {
            // Never replay mutations under a newly created identity.
            state.context = null;
            clearTimeout(state.pollTimer);
            updateControls();
            $('reconnect-btn').classList.remove('hidden');
            throw new Error('Your session expired. Reconnect to prepare a new chat.');
        }
        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`);
        }
        return response.status === 204 ? null : response.json();
    }
    async function allPages(path) {
        const rows = [];
        for (let skip = 0; ; skip += 100) {
            const page = await api(`${path}${path.includes('?') ? '&' : '?'}skip=${skip}&limit=100`);
            rows.push(...page);
            if (page.length < 100) return rows;
        }
    }
    function documentPath() {
        return `/api/v1/workspaces/${state.context.workspace_id}/documents?conversation_id=${state.context.conversation_id}`;
    }
    async function loadDocuments() {
        if (!state.context || state.loadingDocuments) return;
        state.loadingDocuments = true;
        clearTimeout(state.pollTimer);
        try {
            const documents = await allPages(documentPath());
            state.documents = documents;
            renderDocuments();
            $('document-error').classList.add('hidden');
        } catch (error) {
            // Preserve successful upload metadata; this is NOT an upload failure.
            $('document-error').textContent = `Could not refresh the document list. ${error.message} You do not need to upload again.`;
            $('document-error').classList.remove('hidden');
        } finally {
            state.loadingDocuments = false;
            updateControls();
            if (state.context && state.documents.some((doc) => doc.indexing_status === 'processing')) {
                state.pollTimer = setTimeout(loadDocuments, 3000);
            }
        }
    }
    function renderDocuments() {
        const list = $('document-list');
        list.replaceChildren();
        if (!state.documents.length) list.appendChild(el('p', 'hint', 'No documents yet.'));
        for (const doc of state.documents) {
            const row = el('div', 'document-item');
            row.appendChild(el('span', null, doc.file_name));
            row.appendChild(el('span', `status-badge status-${doc.indexing_status}`, doc.indexing_status));
            if (doc.indexing_status === 'failed') row.appendChild(el('span', 'hint', 'Choose the same file to retry.'));
            const deleteBtn = el('button', 'btn btn-delete', 'Delete');
            deleteBtn.disabled = doc.indexing_status === 'processing';
            deleteBtn.onclick = async () => {
                if (!confirm('Delete this document and its indexed data?')) return;
                deleteBtn.disabled = true;
                try {
                    const result = await api(`/api/v1/documents/${doc.id}`, { method: 'DELETE' });
                    if (result && result.diagnostic) showToast('Document removed, but stored-file cleanup was incomplete.');
                    await loadDocuments();
                } catch (error) { showToast(error.message); deleteBtn.disabled = false; }
            };
            row.appendChild(deleteBtn);
            list.appendChild(row);
        }
    }
    async function uploadDocument(file) {
        if (!file || !state.context || state.uploading) return;
        if (!/\.(pdf|txt)$/i.test(file.name) || !file.size || file.size > state.context.max_file_size_bytes) {
            showToast('Choose a nonempty PDF or TXT within the displayed size limit.');
            return;
        }
        state.uploading = true;
        updateControls();
        $('upload-status').textContent = `Uploading and processing ${file.name}…`;
        const data = new FormData();
        data.append('file', file);
        let uploaded;
        try {
            const path = `/api/v1/workspaces/${state.context.workspace_id}/documents/upload?conversation_id=${state.context.conversation_id}`;
            uploaded = await api(path, { method: 'POST', body: data });
            if (uploaded.disposition === 'failed' && confirm('This document previously failed indexing. Retry now?')) {
                uploaded = await api(`${path}&retry=true`, { method: 'POST', body: data });
            }
        } catch (error) {
            $('upload-status').textContent = `Upload or processing could not be confirmed: ${error.message} Refresh status before retrying.`;
        } finally {
            state.uploading = false;
            $('file-input').value = '';
        }
        if (uploaded) {
            const labels = { already_exists: 'Already uploaded', processing: 'Already processing',
                failed: 'Indexing failed; choose the same file to retry', accepted: 'Ready', retried: 'Ready' };
            $('upload-status').textContent = `${uploaded.file_name}: ${labels[uploaded.disposition] || uploaded.indexing_status}.`;
            state.documents = [...state.documents.filter((doc) => doc.id !== uploaded.id), uploaded];
            try { renderDocuments(); } catch (_) { showToast('Upload succeeded, but the document display could not refresh.'); }
        }
        updateControls();
        await loadDocuments();
    }
    async function loadMessages() {
        if (!state.context) return;
        const messages = await allPages(`/api/v1/conversations/${state.context.conversation_id}/messages`);
        renderMessages(messages);
    }
    function renderMessages(messages) {
        const history = $('message-history');
        history.innerHTML = '';

        for (const message of messages) {
            const bubble = el(
                'div',
                `message ${message.sender_role}`,
                message.text
            );

            if (message.sender_role === 'assistant') {
                const sources = message.sources || [];
                if (sources.length > 0) {
                    const container = el('div', 'message-sources');
                    container.appendChild(
                        el('strong', null, 'Sources:')
                    );
                    for (const source of sources) {
                        container.appendChild(renderSource(source));
                    }
                    bubble.appendChild(container);
                }
            }

            history.appendChild(bubble);
        }

        history.scrollTop = history.scrollHeight;
    }

    function renderSource(source) {
        const node = el('div', 'source');
        const page =
            source.page !== null && source.page !== undefined
                ? `, page ${source.page}`
                : '';
        node.appendChild(
            el(
                'strong',
                null,
                `${source.filename}${page} (chunk ${source.chunk_id})`
            )
        );
        if (source.snippet) {
            node.appendChild(
                el('div', 'source-snippet', source.snippet)
            );
        }
        return node;
    }

    async function sendChatMessage(event) {
        event.preventDefault();
        if (state.chatSubmitting || $('send-chat-btn').disabled || !state.context) return;
        const question = $('chat-input').value.trim();
        if (!question) return;
        state.chatSubmitting = true;
        updateControls();
        $('chat-loading').classList.remove('hidden');
        try {
            const result = await api(`/api/v1/conversations/${state.context.conversation_id}/chat`, {
                method: 'POST', body: JSON.stringify({ question }),
            });
            $('chat-input').value = '';
            if (result.insufficient_context) showToast('No supporting context was found in these documents.');
        } catch (error) { showToast(error.message); }
        finally {
            try { await loadMessages(); } catch (_) { showToast('Could not refresh conversation history. Refresh the page; do not resend automatically.'); }
            state.chatSubmitting = false;
            $('chat-loading').classList.add('hidden');
            updateControls();
        }
    }
    async function init() {
        $('reconnect-btn').disabled = true;
        try {
            // Browser sends HttpOnly cookies; only the server checks validity.
            await api('/api/v1/sessions', { method: 'POST' });
            state.context = await api('/api/v1/sessions/context', { method: 'POST' });
            state.documents = [];
            $('message-history').replaceChildren();
            $('upload-status').textContent = '';
            $('upload-hint').textContent = `PDF or TXT, up to ${state.context.max_file_size_bytes / 1024 / 1024} MB. Keep this browser cookie to retain access.`;
            await loadDocuments();
            await loadMessages();
            $('initialization-status').textContent = 'Your chat is ready.';
            $('reconnect-btn').classList.add('hidden');
        } catch (error) {
            showToast(error.message);
            $('initialization-status').textContent = 'Could not restore your chat.';
            $('reconnect-btn').classList.remove('hidden');
        } finally { $('reconnect-btn').disabled = false; updateControls(); }
    }
    $('upload-area').onclick = () => $('file-input').click();
    $('file-input').onchange = () => uploadDocument($('file-input').files[0]);
    document.addEventListener('dragover', (event) => { event.preventDefault(); });
    document.addEventListener('drop', (event) => {
        event.preventDefault();
        if (event.dataTransfer.files.length !== 1) { showToast('Please upload one file at a time.'); return; }
        uploadDocument(event.dataTransfer.files[0]);
    });
    $('refresh-documents-btn').onclick = loadDocuments;
    $('reconnect-btn').onclick = init;
    $('chat-form').onsubmit = sendChatMessage;
    init();
});
