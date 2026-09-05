/**
 * Ox Alpha Web Chat Application
 * Handles chat sessions, real-time SSE streaming, markdown rendering, and responsive UI.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const sidebar = document.getElementById('sidebar');
  const collapseSidebarBtn = document.getElementById('collapseSidebarBtn');
  const openMobileSidebarBtn = document.getElementById('openMobileSidebarBtn');
  const newChatBtn = document.getElementById('newChatBtn');
  const mobileNewChatBtn = document.getElementById('mobileNewChatBtn');
  const chatList = document.getElementById('chatList');
  const heroGreeting = document.getElementById('heroGreeting');
  const messagesContainer = document.getElementById('messagesContainer');
  const messagesFeed = document.getElementById('messagesFeed');
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const displayModelName = document.getElementById('displayModelName');

  // State
  let sessions = JSON.parse(localStorage.getItem('gravix_chat_sessions') || '[]');
  let currentSessionId = localStorage.getItem('gravix_current_session_id') || null;
  let isStreaming = false;

  // Initialize marked options
  if (window.marked) {
    marked.setOptions({
      breaks: true,
      gfm: true,
      highlight: function (code, lang) {
        if (window.hljs && lang && hljs.getLanguage(lang)) {
          try {
            return hljs.highlight(code, { language: lang }).value;
          } catch (e) {}
        }
        return code;
      }
    });
  }

  // --- Session Management ---
  function saveSessions() {
    localStorage.setItem('gravix_chat_sessions', JSON.stringify(sessions));
    localStorage.setItem('gravix_current_session_id', currentSessionId);
  }

  function getActiveSession() {
    return sessions.find(s => s.id === currentSessionId);
  }

  function createNewSession() {
    const newSession = {
      id: 'session_' + Date.now(),
      title: 'New Chat',
      messages: [],
      createdAt: Date.now()
    };
    sessions.unshift(newSession);
    currentSessionId = newSession.id;
    saveSessions();
    renderSidebar();
    renderMessages();
    messageInput.focus();
  }

  function deleteSession(sessionId, event) {
    event.stopPropagation();
    sessions = sessions.filter(s => s.id !== sessionId);
    if (currentSessionId === sessionId) {
      currentSessionId = sessions.length > 0 ? sessions[0].id : null;
    }
    if (!currentSessionId) {
      createNewSession();
    } else {
      saveSessions();
      renderSidebar();
      renderMessages();
    }
  }

  function switchSession(sessionId) {
    if (isStreaming) return;
    currentSessionId = sessionId;
    saveSessions();
    renderSidebar();
    renderMessages();
    if (window.innerWidth <= 768) {
      sidebar.classList.remove('open');
    }
  }

  // --- UI Rendering ---
  function renderSidebar() {
    chatList.innerHTML = '';
    sessions.forEach(session => {
      const item = document.createElement('div');
      item.className = `chat-item ${session.id === currentSessionId ? 'active' : ''}`;
      item.onclick = () => switchSession(session.id);

      const titleSpan = document.createElement('span');
      titleSpan.className = 'chat-item-title';
      titleSpan.textContent = session.title || 'New Chat';

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'delete-chat-btn';
      deleteBtn.title = 'Delete chat';
      deleteBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
      `;
      deleteBtn.onclick = (e) => deleteSession(session.id, e);

      item.appendChild(titleSpan);
      item.appendChild(deleteBtn);
      chatList.appendChild(item);
    });
  }

  function sanitizeBrandDisplay(text) {
    if (!text) return '';
    return text
      .replace(/ox\s*alpha/gi, 'Gravix AI')
      .replace(/\boxalpha\.com\b/gi, 'gravix.ai')
      .replace(/\boxalpha\b/gi, 'Gravix AI')
      .replace(/\bglm(-[\w\.]+)?\b/gi, 'Gravix AI')
      .replace(/\bzhipu(\s*ai)?\b/gi, 'Gravix')
      .replace(/\bz\.ai\b/gi, 'Gravix');
  }

  function renderMessages() {
    const session = getActiveSession();
    messagesFeed.innerHTML = '';

    if (!session || session.messages.length === 0) {
      heroGreeting.classList.remove('hidden');
      return;
    }

    heroGreeting.classList.add('hidden');
    session.messages.forEach(msg => {
      const displayContent = msg.role === 'assistant' ? sanitizeBrandDisplay(msg.content) : msg.content;
      appendMessageToDOM(msg.role, displayContent, false);
    });
    scrollToBottom();
  }

  function appendMessageToDOM(role, content, isLive = false) {
    heroGreeting.classList.add('hidden');

    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    if (role === 'user') {
      const bubble = document.createElement('div');
      bubble.className = 'user-bubble';
      bubble.textContent = content;
      row.appendChild(bubble);
    } else {
      const bubble = document.createElement('div');
      bubble.className = 'assistant-bubble';
      if (isLive) {
        bubble.innerHTML = '<span class="streaming-cursor"></span>';
      } else {
        const cleanContent = sanitizeBrandDisplay(content);
        bubble.innerHTML = renderMarkdown(cleanContent);
        attachCodeCopyButtons(bubble);
      }
      row.appendChild(bubble);
    }

    messagesFeed.appendChild(row);
    scrollToBottom();
    return row;
  }

  function renderMarkdown(text) {
    if (window.marked) {
      return marked.parse(text || '');
    }
    return text.replace(/\n/g, '<br>');
  }

  function attachCodeCopyButtons(container) {
    const preBlocks = container.querySelectorAll('pre');
    preBlocks.forEach(pre => {
      if (pre.querySelector('.code-header')) return;

      const code = pre.querySelector('code');
      const langMatch = code ? code.className.match(/language-(\w+)/) : null;
      const lang = langMatch ? langMatch[1] : 'code';

      const header = document.createElement('div');
      header.className = 'code-header';
      header.innerHTML = `
        <span>${lang}</span>
        <button class="copy-code-btn" type="button">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          Copy
        </button>
      `;

      const copyBtn = header.querySelector('.copy-code-btn');
      copyBtn.onclick = () => {
        const textToCopy = code ? code.innerText : pre.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
          copyBtn.innerHTML = '✓ Copied!';
          setTimeout(() => {
            copyBtn.innerHTML = `
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              Copy
            `;
          }, 2000);
        });
      };

      pre.insertBefore(header, pre.firstChild);
    });
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // --- Auto-resize Textarea ---
  function adjustTextarea() {
    messageInput.style.height = 'auto';
    const newHeight = Math.min(messageInput.scrollHeight, 180);
    messageInput.style.height = newHeight + 'px';

    const hasText = messageInput.value.trim().length > 0;
    sendBtn.disabled = !hasText || isStreaming;
    if (hasText && !isStreaming) {
      sendBtn.classList.add('active');
    } else {
      sendBtn.classList.remove('active');
    }
  }

  messageInput.addEventListener('input', adjustTextarea);
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        chatForm.dispatchEvent(new Event('submit'));
      }
    }
  });

  // --- Streaming Chat Submission ---
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const prompt = messageInput.value.trim();
    if (!prompt || isStreaming) return;

    let session = getActiveSession();
    if (!session) {
      createNewSession();
      session = getActiveSession();
    }

    // Set chat title from first prompt
    if (session.messages.length === 0) {
      session.title = prompt.length > 28 ? prompt.substring(0, 28) + '...' : prompt;
      renderSidebar();
    }

    // Append user message
    session.messages.push({ role: 'user', content: prompt });
    appendMessageToDOM('user', prompt);
    saveSessions();

    // Reset input
    messageInput.value = '';
    adjustTextarea();
    isStreaming = true;
    sendBtn.disabled = true;
    sendBtn.classList.remove('active');

    // Create assistant streaming placeholder
    const assistantRow = appendMessageToDOM('assistant', '', true);
    const bubble = assistantRow.querySelector('.assistant-bubble');

    let accumulatedContent = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'gravix-ai',
          messages: session.messages,
          stream: true
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `Server returned ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep last unfinished line

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          const dataStr = trimmed.slice(5).trim();
          if (dataStr === '[DONE]') break;

          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.choices && parsed.choices[0].delta && parsed.choices[0].delta.content) {
              accumulatedContent += parsed.choices[0].delta.content;
              const liveClean = sanitizeBrandDisplay(accumulatedContent);
              bubble.innerHTML = renderMarkdown(liveClean) + '<span class="streaming-cursor"></span>';
              scrollToBottom();
            }
          } catch (err) {
            // Ignore malformed chunk lines
          }
        }
      }

      // Finished streaming
      const finalClean = sanitizeBrandDisplay(accumulatedContent);
      bubble.innerHTML = renderMarkdown(finalClean);
      attachCodeCopyButtons(bubble);
      session.messages.push({ role: 'assistant', content: finalClean });
      saveSessions();
    } catch (err) {
      console.error('Streaming error:', err);
      bubble.innerHTML = `<span style="color: #ef4444;">Error: ${err.message || 'Failed to receive response.'}</span>`;
      session.messages.push({ role: 'assistant', content: `Error: ${err.message}` });
      saveSessions();
    } finally {
      isStreaming = false;
      adjustTextarea();
      messageInput.focus();
    }
  });

  // --- Sidebar Collapse / Open Handlers ---
  collapseSidebarBtn.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
  });

  openMobileSidebarBtn.addEventListener('click', () => {
    sidebar.classList.add('open');
  });

  newChatBtn.addEventListener('click', createNewSession);
  mobileNewChatBtn.addEventListener('click', createNewSession);

  // Close mobile sidebar on outside click
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target) && !openMobileSidebarBtn.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    }
  });

  // Initial Load
  if (sessions.length === 0) {
    createNewSession();
  } else {
    if (!currentSessionId || !getActiveSession()) {
      currentSessionId = sessions[0].id;
    }
    renderSidebar();
    renderMessages();
  }
});
