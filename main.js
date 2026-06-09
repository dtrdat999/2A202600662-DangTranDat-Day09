// main.js - Logic for chatting with Stage 4 Backend

const chatForm = document.getElementById('chat-form');
const questionInput = document.getElementById('question-input');
const chatContainer = document.getElementById('chat-container');
const sendBtn = document.getElementById('send-btn');

// Topology Nodes
const nodes = {
  law: document.getElementById('agent-law'),
  tax: document.getElementById('agent-tax'),
  compliance: document.getElementById('agent-compliance'),
  privacy: document.getElementById('agent-privacy'),
  aggregate: document.getElementById('agent-aggregate')
};

const paths = {
  p1: document.getElementById('path-1'),
  p2: document.getElementById('path-2')
};

// Configure marked.js options
marked.setOptions({
  breaks: true,
  gfm: true
});

// Auto-resize textarea
questionInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 150) + 'px';
  sendBtn.disabled = this.value.trim().length === 0;
});

// Submit on Enter (Shift+Enter for new line)
questionInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (this.value.trim().length > 0) {
      chatForm.dispatchEvent(new Event('submit'));
    }
  }
});

function createMessageElement(sender, content, isMarkdown = false) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}-msg`;
  
  const icon = sender === 'user' ? 'fa-user' : 'fa-sparkles';
  let displayContent = content;

  if (isMarkdown) {
    // Parse markdown and sanitize HTML
    const rawHtml = marked.parse(content);
    displayContent = DOMPurify.sanitize(rawHtml);
  }

  msgDiv.innerHTML = `
    <div class="avatar"><i class="fa-solid ${icon}"></i></div>
    <div class="msg-content ${isMarkdown ? 'markdown-body' : ''}">${displayContent}</div>
  `;
  
  return msgDiv;
}

function appendMessage(sender, content, isMarkdown = false) {
  const msgDiv = createMessageElement(sender, content, isMarkdown);
  chatContainer.appendChild(msgDiv);
  scrollToBottom();
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Graph Animation Logic
function setNodeState(nodeKey, state) {
  const el = nodes[nodeKey];
  if (!el) return;
  el.className = `agent-node ${el.classList.contains('small') ? 'small' : ''}`;
  if (state) {
    el.classList.add(state);
  }
}

function setPathState(pathKey, state) {
  const el = paths[pathKey];
  if (!el) return;
  el.className = 'path-line';
  if (state) {
    el.classList.add(state);
  }
}

function resetTopology() {
  Object.keys(nodes).forEach(k => setNodeState(k, null));
  Object.keys(paths).forEach(k => setPathState(k, null));
}

const sessionId = "session-" + Date.now() + "-" + Math.floor(Math.random() * 1000);

// Orchestrate the animation timeline
async function animateTopology(data) {
  // 1. Law Agent starts analyzing
  setNodeState('law', 'active');
  await new Promise(r => setTimeout(r, 1200));
  
  // 2. Routing to parallel agents
  setPathState('p1', 'active');
  await new Promise(r => setTimeout(r, 800));
  setNodeState('law', 'done');
  setPathState('p1', null);
  
  // 3. Parallel agents process
  const activeSpecialists = [];
  if (data.tax_result) activeSpecialists.push('tax');
  if (data.compliance_result) activeSpecialists.push('compliance');
  if (data.privacy_result) activeSpecialists.push('privacy');
  
  // If none (which is rare), fallback
  if (activeSpecialists.length === 0) activeSpecialists.push('tax', 'compliance', 'privacy');

  activeSpecialists.forEach(s => setNodeState(s, 'active'));
  
  // Wait for parallel processing
  await new Promise(r => setTimeout(r, 2000));
  
  // 4. Routing to aggregator
  setPathState('p2', 'active');
  await new Promise(r => setTimeout(r, 800));
  
  activeSpecialists.forEach(s => setNodeState(s, 'done'));
  setPathState('p2', null);
  
  // 5. Aggregator synthesizes
  setNodeState('aggregate', 'active');
  await new Promise(r => setTimeout(r, 1500));
  setNodeState('aggregate', 'done');
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const text = questionInput.value.trim();
  if (!text) return;
  
  // UI State: disable
  questionInput.value = '';
  questionInput.style.height = 'auto';
  sendBtn.disabled = true;
  questionInput.disabled = true;
  
  appendMessage('user', text);
  resetTopology();
  
  // Show Loading indicator
  const loadingId = 'loading-' + Date.now();
  const loadingDiv = document.createElement('div');
  loadingDiv.className = `message system-msg`;
  loadingDiv.id = loadingId;
  loadingDiv.innerHTML = `
    <div class="avatar"><i class="fa-solid fa-sparkles"></i></div>
    <div class="msg-content">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  chatContainer.appendChild(loadingDiv);
  scrollToBottom();

  try {
    // API Call
    const response = await fetch('http://127.0.0.1:8000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        question: text,
        thread_id: sessionId
      })
    });
    
    if (!response.ok) throw new Error("API Error: " + response.statusText);
    
    const data = await response.json();
    
    // Simulate orchestration animation before showing result
    await animateTopology(data);
    
    // Remove loading
    document.getElementById(loadingId).remove();
    
    // Append actual formatted markdown answer
    appendMessage('system', data.final_answer, true);
    
  } catch (err) {
    document.getElementById(loadingId).remove();
    appendMessage('system', '**Lỗi Kết Nối:** Không thể liên lạc với Backend. Hãy đảm bảo uvicorn đang chạy trên cổng 8000.\n\n`' + err.message + '`', true);
    console.error(err);
  } finally {
    // UI State: enable
    sendBtn.disabled = false;
    questionInput.disabled = false;
    questionInput.focus();
  }
});

// Init
questionInput.focus();
sendBtn.disabled = true;
