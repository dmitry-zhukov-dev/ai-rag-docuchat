document.addEventListener('DOMContentLoaded', () => {
    const SESSION_COOKIE = 'docuchat_session';

    // ---------- State ----------
    const state = {
        workspaces: [],
        selectedWorkspace: null,
        documents: [],
        selectedDocumentIds: new Set(),
        conversations: [],
        selectedConversation: null,
        evaluationCases: [],
        selectedEvaluationCase: null,
        chatSubmitting: false,
        evaluationRunning: false,
        pollTimer: null,
    };

    // ---------- DOM helpers ----------
    const $ = (id) => document.getElementById(id);

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function showToast(message) {
        const toast = $('app-error');
        toast.textContent = message;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 6000);
    }

    function showSectionError(elementId, message) {
        const element = $(elementId);
        element.textContent = message;
        element.classList.remove('hidden');
    }

    function clearSectionError(elementId) {
        $(elementId).classList.add('hidden');
    }

    // ---------- API ----------
    async function api(path, options = {}) {
        const response = await fetch(path, {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });

        if (response.status === 401) {
            // The session expired: start a new one and
            // retry the request exactly once.
            await createSession();
            const retry = await fetch(path, {
                headers: { 'Content-Type': 'application/json' },
                ...options,
            });
            if (!retry.ok) throw new Error('Please refresh the page.');
            return retry.json();
        }

        if (!response.ok) {
            let detail = `Request failed (${response.status})`;
            try {
                const body = await response.json();
                if (body && body.detail) detail = body.detail;
            } catch (_) {
                // Keep the generic message.
            }
            throw new Error(detail);
        }

        if (response.status === 204) return null;
        return response.json();
    }

    function getCookie(name) {
        const prefix = name + '=';
        for (const part of document.cookie.split(';')) {
            const entry = part.trim();
            if (entry.startsWith(prefix)) {
                return entry.substring(prefix.length);
            }
        }
        return null;
    }

    async function createSession() {
        await api('/api/v1/sessions', { method: 'POST' });
    }

    // ---------- Workspaces ----------
    async function loadWorkspaces() {
        $('workspace-loading').classList.remove('hidden');
        $('workspace-error').classList.add('hidden');
        try {
            state.workspaces = await api('/api/v1/workspaces/');
            renderWorkspaces();
        } catch (error) {
            $('workspace-error').classList.remove('hidden');
        } finally {
            $('workspace-loading').classList.add('hidden');
        }
    }

    function renderWorkspaces() {
        const list = $('workspace-list');
        list.innerHTML = '';

        if (state.workspaces.length === 0) {
            list.appendChild(
                el('p', null, 'No workspaces yet. Create one to begin.')
            );
            return;
        }

        for (const workspace of state.workspaces) {
            const item = el('div', 'workspace-item', workspace.name);
            if (
                state.selectedWorkspace &&
                workspace.id === state.selectedWorkspace.id
            ) {
                item.classList.add('selected');
            }
            item.onclick = () => selectWorkspace(workspace);
            list.appendChild(item);
        }
    }

    async function selectWorkspace(workspace) {
        state.selectedWorkspace = workspace;
        state.selectedConversation = null;
        state.selectedDocumentIds = new Set();
        state.selectedEvaluationCase = null;
        renderWorkspaces();
        $('workspace-name').textContent = workspace.name;
        $('empty-state').classList.add('hidden');
        $('workspace-view').classList.remove('hidden');
        await Promise.all([
            loadDocuments(),
            loadConversations(),
            loadEvaluationCases(),
        ]);
    }

    // ---------- Documents ----------
    async function loadDocuments() {
        if (!state.selectedWorkspace) return;
        try {
            state.documents = await api(
                `/api/v1/workspaces/${state.selectedWorkspace.id}/documents`
            );
            renderDocuments();
        } catch (error) {
            showSectionError('document-error', 'Failed to load documents.');
        }
    }

    function renderDocuments() {
        const list = $('document-list');
        list.innerHTML = '';
        clearSectionError('document-error');

        if (state.documents.length === 0) {
            list.appendChild(
                el('p', null, 'No documents uploaded yet.')
            );
            return;
        }

        for (const document of state.documents) {
            const row = el('div', 'document-item');
            const ready = document.indexing_status === 'completed';

            const label = el('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = state.selectedDocumentIds.has(
                document.id
            );
            checkbox.disabled = !ready;
            checkbox.onchange = () => {
                if (checkbox.checked) {
                    state.selectedDocumentIds.add(document.id);
                } else {
                    state.selectedDocumentIds.delete(document.id);
                }
            };
            label.appendChild(checkbox);
            label.appendChild(
                el(
                    'span',
                    null,
                    `${document.file_name} (${document.file_format})`
                )
            );
            row.appendChild(label);

            const badge = el(
                'span',
                `status-badge status-${document.indexing_status}`,
                document.indexing_status
            );
            row.appendChild(badge);

            if (document.error_message) {
                row.appendChild(
                    el('span', 'error-message', document.error_message)
                );
            }

            const deleteBtn = el('button', 'btn btn-delete', 'Delete');
            deleteBtn.onclick = () => deleteDocument(document.id);
            row.appendChild(deleteBtn);

            list.appendChild(row);
        }

        // While any document is still processing, poll for
        // status changes.
        const processing = state.documents.some(
            (document) => document.indexing_status === 'processing'
        );
        if (processing && !state.pollTimer) {
            state.pollTimer = setInterval(loadDocuments, 3000);
        } else if (!processing && state.pollTimer) {
            clearInterval(state.pollTimer);
            state.pollTimer = null;
        }
    }

    async function uploadDocument() {
        if (!state.selectedWorkspace) return;
        const input = $('file-input');
        const file = input.files && input.files[0];

        if (!file) {
            showToast('Choose a TXT or PDF file first.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        $('upload-loading').classList.remove('hidden');
        try {
            const response = await fetch(
                `/api/v1/workspaces/${state.selectedWorkspace.id}/documents/upload`,
                { method: 'POST', body: formData }
            );
            if (!response.ok) {
                const body = await response.json().catch(() => ({}));
                throw new Error(body.detail || 'Upload failed');
            }
            input.value = '';
            await loadDocuments();
        } catch (error) {
            showToast(error.message);
        } finally {
            $('upload-loading').classList.add('hidden');
        }
    }

    async function deleteDocument(documentId) {
        if (!confirm('Delete this document and its indexed data?')) return;
        try {
            await api(`/api/v1/documents/${documentId}`, {
                method: 'DELETE',
            });
            state.selectedDocumentIds.delete(documentId);
            await loadDocuments();
        } catch (error) {
            showToast(error.message);
        }
    }

    // ---------- Conversations and chat ----------
    async function loadConversations() {
        if (!state.selectedWorkspace) return;
        try {
            state.conversations = await api(
                `/api/v1/workspaces/${state.selectedWorkspace.id}/conversations`
            );
            renderConversations();
        } catch (error) {
            showToast('Failed to load conversations.');
        }
    }

    function renderConversations() {
        const list = $('conversation-list');
        list.innerHTML = '';

        for (const conversation of state.conversations) {
            const button = el(
                'button',
                null,
                conversation.title || 'Untitled Chat'
            );
            if (
                state.selectedConversation &&
                conversation.id === state.selectedConversation.id
            ) {
                button.classList.add('selected');
            }
            button.onclick = () => selectConversation(conversation);
            list.appendChild(button);
        }
    }

    async function createConversation() {
        if (!state.selectedWorkspace) return;
        const title = prompt('Chat title:') || 'Untitled Chat';
        const conversation = await api(
            `/api/v1/workspaces/${state.selectedWorkspace.id}/conversations`,
            {
                method: 'POST',
                body: JSON.stringify({ title }),
            }
        ).catch((error) => {
            showToast(error.message);
            return null;
        });
        if (conversation) await selectConversation(conversation);
    }

    async function selectConversation(conversation) {
        state.selectedConversation = conversation;
        renderConversations();
        $('chat-window').classList.remove('hidden');
        $('chat-title').textContent = conversation.title || 'Conversation';
        await loadMessages();
    }

    async function loadMessages() {
        if (!state.selectedConversation) return;
        const messages = await api(
            `/api/v1/conversations/${state.selectedConversation.id}/messages`
        ).catch(() => []);
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

    async function sendChatMessage() {
        if (
            state.chatSubmitting ||
            !state.selectedConversation
        ) {
            return;
        }

        const input = $('chat-input');
        const question = input.value.trim();
        if (!question) return;

        state.chatSubmitting = true;
        $('send-chat-btn').disabled = true;
        $('chat-loading').classList.remove('hidden');
        input.value = '';

        const body = { question };
        if (state.selectedDocumentIds.size > 0) {
            body.document_ids = Array.from(
                state.selectedDocumentIds
            );
        }

        try {
            await api(
                `/api/v1/conversations/${state.selectedConversation.id}/chat`,
                { method: 'POST', body: JSON.stringify(body) }
            );
            await loadMessages();
        } catch (error) {
            showToast(error.message);
        } finally {
            $('chat-loading').classList.add('hidden');
            $('send-chat-btn').disabled = false;
            state.chatSubmitting = false;
        }
    }

    // ---------- Evaluation ----------
    async function loadEvaluationCases() {
        if (!state.selectedWorkspace) return;
        try {
            state.evaluationCases = await api(
                `/api/v1/workspaces/${state.selectedWorkspace.id}/evaluations`
            );
            renderEvaluationCases();
        } catch (error) {
            // Evaluation is an optional panel; surface
            // failures without breaking the main workflow.
        }
    }

    function renderEvaluationCases() {
        const list = $('evaluation-list');
        list.innerHTML = '';

        for (const testCase of state.evaluationCases) {
            const button = el('button', null, testCase.name);
            if (
                state.selectedEvaluationCase &&
                testCase.id === state.selectedEvaluationCase.id
            ) {
                button.classList.add('selected');
            }
            button.onclick = () => selectEvaluationCase(testCase);
            list.appendChild(button);
        }
    }

    function selectEvaluationCase(testCase) {
        state.selectedEvaluationCase = testCase;
        renderEvaluationCases();
        $('evaluation-editor').classList.remove('hidden');
        $('evaluation-editor-title').textContent = testCase.name;
        $('evaluation-name').value = testCase.name;
        $('evaluation-question').value = testCase.question;
        $('evaluation-reference').value =
            testCase.reference_answer || '';
        $('evaluation-facts').value = (
            testCase.required_facts || []
        ).join('\n');
        $('evaluation-expected-sources').value = (
            testCase.expected_sources || []
        )
            .map((source) => source.document_id)
            .join(', ');
        $('evaluation-run-btn').disabled =
            testCase.indexing_status === undefined;
        renderEvaluationDocumentSelection(testCase);
        $('evaluation-results').classList.add('hidden');
    }

    function renderEvaluationDocumentSelection(testCase) {
        const container = $('evaluation-document-list');
        container.innerHTML = '';

        for (const document of state.documents) {
            if (document.indexing_status !== 'completed') continue;
            const label = el('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = (
                testCase.selected_document_ids || []
            ).includes(document.id);
            checkbox.onchange = () => {
                testCase.selected_document_ids =
                    testCase.selected_document_ids || [];
                if (checkbox.checked) {
                    testCase.selected_document_ids.push(
                        document.id
                    );
                } else {
                    testCase.selected_document_ids =
                        testCase.selected_document_ids.filter(
                            (id) => id !== document.id
                        );
                }
            };
            label.appendChild(checkbox);
            label.appendChild(
                el('span', null, document.file_name)
            );
            container.appendChild(label);
        }
    }

    async function saveEvaluationCase() {
        const testCase = state.selectedEvaluationCase;
        if (!testCase) return;

        const payload = {
            name: $('evaluation-name').value.trim(),
            question: $('evaluation-question').value.trim(),
            reference_answer: $('evaluation-reference').value.trim(),
            required_facts: $('evaluation-facts').value
                .split('\n')
                .map((line) => line.trim())
                .filter(Boolean),
            expected_sources: $('evaluation-expected-sources')
                .value.split(',')
                .map((value) => value.trim())
                .filter(Boolean)
                .map((documentId) => ({ document_id: documentId })),
            selected_document_ids:
                testCase.selected_document_ids || [],
        };

        try {
            const saved = testCase.id
                ? await api(`/api/v1/evaluations/${testCase.id}`, {
                      method: 'PATCH',
                      body: JSON.stringify(payload),
                  })
                : await api(
                      `/api/v1/workspaces/${state.selectedWorkspace.id}/evaluations`,
                      {
                          method: 'POST',
                          body: JSON.stringify(payload),
                      }
                  );
            await loadEvaluationCases();
            selectEvaluationCase(saved);
        } catch (error) {
            showToast(error.message);
        }
    }

    async function deleteEvaluationCase() {
        const testCase = state.selectedEvaluationCase;
        if (!testCase || !testCase.id) return;
        if (!confirm('Delete this test case and its runs?')) return;

        try {
            await api(`/api/v1/evaluations/${testCase.id}`, {
                method: 'DELETE',
            });
            state.selectedEvaluationCase = null;
            $('evaluation-editor').classList.add('hidden');
            await loadEvaluationCases();
        } catch (error) {
            showToast(error.message);
        }
    }

    async function runEvaluationCase() {
        const testCase = state.selectedEvaluationCase;
        if (!testCase || state.evaluationRunning) return;

        state.evaluationRunning = true;
        $('evaluation-run-btn').disabled = true;
        $('evaluation-run-status').classList.remove('hidden');
        $('evaluation-results-table').classList.add('hidden');
        $('evaluation-error').classList.add('hidden');

        try {
            const run = await api(
                `/api/v1/evaluations/${testCase.id}/runs`,
                { method: 'POST' }
            );
            await pollEvaluationRun(run.id);
        } catch (error) {
            showSectionError('evaluation-error', error.message);
        } finally {
            state.evaluationRunning = false;
            $('evaluation-run-btn').disabled = false;
            $('evaluation-run-status').classList.add('hidden');
        }
    }

    async function pollEvaluationRun(runId) {
        const run = await api(`/api/v1/evaluation-runs/${runId}`);

        if (run.status === 'running' || run.status === 'pending') {
            setTimeout(() => pollEvaluationRun(runId), 2000);
            return;
        }

        renderEvaluationRun(run);
    }

    function renderEvaluationRun(run) {
        const results = $('evaluation-results');
        results.classList.remove('hidden');

        const table = $('evaluation-results-table');
        const body = $('evaluation-results-body');
        table.classList.remove('hidden');
        body.innerHTML = '';

        const metrics = run.metrics || {};
        for (const [key, value] of Object.entries(metrics)) {
            const row = el('tr');
            row.appendChild(el('td', null, key));
            row.appendChild(el('td', null, String(value)));
            body.appendChild(row);
        }

        const answer = $('evaluation-answer');
        answer.classList.remove('hidden');
        answer.textContent = `Answer: ${run.answer || '(none)'}`;

        const sources = $('evaluation-sources');
        sources.classList.remove('hidden');
        sources.innerHTML = '';
        sources.appendChild(el('strong', null, 'Sources used:'));
        for (const source of run.actual_sources || []) {
            sources.appendChild(renderSource(source));
        }

        if (run.error) {
            showSectionError('evaluation-error', run.error);
        }
    }

    // ---------- Wiring ----------
    $('create-workspace-btn').onclick = async () => {
        const name = prompt('Workspace name:');
        if (!name || !name.trim()) return;
        try {
            const workspace = await api('/api/v1/workspaces/', {
                method: 'POST',
                body: JSON.stringify({ name: name.trim() }),
            });
            await loadWorkspaces();
            await selectWorkspace(workspace);
        } catch (error) {
            showToast(error.message);
        }
    };

    $('delete-workspace-btn').onclick = async () => {
        if (!state.selectedWorkspace) return;
        if (
            !confirm(
                `Delete workspace "${state.selectedWorkspace.name}" and all of its data?`
            )
        ) {
            return;
        }
        try {
            await api(
                `/api/v1/workspaces/${state.selectedWorkspace.id}`,
                { method: 'DELETE' }
            );
            state.selectedWorkspace = null;
            $('workspace-view').classList.add('hidden');
            $('empty-state').classList.remove('hidden');
            await loadWorkspaces();
        } catch (error) {
            showToast(error.message);
        }
    };

    $('upload-btn').onclick = uploadDocument;
    $('refresh-documents-btn').onclick = loadDocuments;
    $('new-chat-btn').onclick = createConversation;
    $('send-chat-btn').onclick = sendChatMessage;
    $('chat-input').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') sendChatMessage();
    });

    $('new-evaluation-btn').onclick = () => {
        state.selectedEvaluationCase = {
            id: null,
            name: 'New test case',
            question: '',
            reference_answer: '',
            required_facts: [],
            expected_sources: [],
            selected_document_ids: [],
        };
        selectEvaluationCase(state.selectedEvaluationCase);
    };
    $('evaluation-save-btn').onclick = saveEvaluationCase;
    $('evaluation-run-btn').onclick = runEvaluationCase;
    $('evaluation-delete-btn').onclick = deleteEvaluationCase;
    $('evaluation-cancel-btn').onclick = () => {
        state.selectedEvaluationCase = null;
        $('evaluation-editor').classList.add('hidden');
        $('evaluation-results').classList.add('hidden');
        renderEvaluationCases();
    };

    // ---------- Initialization ----------
    (async function init() {
        try {
            // Start (or reuse) the anonymous session;
            // the server sets the session cookie.
            if (!getCookie(SESSION_COOKIE)) {
                await createSession();
            }
            await loadWorkspaces();
        } catch (error) {
            showToast('Failed to initialize the application.');
        }
    })();
});
