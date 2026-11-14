/**
 * Financial Chatbot Module
 * Manages chat UI interactions, suggested prompt execution, message formatting, and guardrail responses.
 */

const Chatbot = (() => {
    const messagesContainer = document.getElementById("chatMessages");
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const suggestedContainer = document.getElementById("suggestedPromptsContainer");

    function init() {
        if (!chatForm) return;

        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;
            await sendMessage(text);
        });

        loadSuggestedPrompts();
    }

    async function loadSuggestedPrompts() {
        try {
            const data = await Api.get("/api/v1/chatbot/suggested-prompts");
            if (data.suggested_prompts && suggestedContainer) {
                suggestedContainer.innerHTML = data.suggested_prompts
                    .map(prompt => `<button class="prompt-pill" type="button">${escapeHtml(prompt)}</button>`)
                    .join("");

                suggestedContainer.querySelectorAll(".prompt-pill").forEach(btn => {
                    btn.addEventListener("click", () => {
                        chatInput.value = btn.textContent;
                        chatInput.focus();
                        sendMessage(btn.textContent);
                    });
                });
            }
        } catch (err) {
            console.warn("Failed to load suggested prompts:", err);
        }
    }

    async function sendMessage(text) {
        if (!Api.getToken()) {
            window.App?.showToast("Please sign in or choose a demo role to chat.", "info");
            window.App?.openLoginModal();
            return;
        }

        // Append user message
        appendMessage(text, "user");
        chatInput.value = "";

        // Add typing indicator
        const typingId = appendTypingIndicator();

        try {
            const res = await Api.post("/api/v1/chatbot/message", { prompt: text });
            removeTypingIndicator(typingId);

            let contentHtml = `<p><strong>${escapeHtml(res.topic || "Analysis")}</strong></p>`;
            contentHtml += `<p>${formatBotResponse(res.reply)}</p>`;

            if (res.calculation_tip) {
                contentHtml += `<div class="calc-tip" style="margin-top:0.5rem; padding:0.5rem; background:rgba(99,102,241,0.1); border-radius:6px; font-size:0.8rem;">
                    💡 <strong>Calculation Tip:</strong> ${escapeHtml(res.calculation_tip)}
                </div>`;
            }

            if (res.disclaimer) {
                contentHtml += `<div class="message-disclaimer"><small>ℹ️ ${escapeHtml(res.disclaimer)}</small></div>`;
            }

            appendMessage(contentHtml, "bot", true);
        } catch (err) {
            removeTypingIndicator(typingId);
            const errData = err.data || {};
            if (errData.is_security_violation) {
                appendMessage(
                    `⚠️ <strong>Security Violation Detected:</strong><br>${escapeHtml(errData.error)}<br><small style="color:var(--danger)">${escapeHtml(errData.violation_reason || "")}</small>`,
                    "bot",
                    true
                );
            } else {
                appendMessage(
                    `❌ <strong>Error:</strong> ${escapeHtml(err.message || "Failed to process question. Please try again.")}`,
                    "bot",
                    true
                );
            }
        }
    }

    function appendMessage(content, sender, isHtml = false) {
        if (!messagesContainer) return;
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender === "user" ? "user-msg" : "bot-message"}`;
        
        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        if (isHtml) {
            bubble.innerHTML = content;
        } else {
            bubble.textContent = content;
        }

        msgDiv.appendChild(bubble);
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function appendTypingIndicator() {
        const id = "typing-" + Date.now();
        const msgDiv = document.createElement("div");
        msgDiv.id = id;
        msgDiv.className = "message bot-message";
        msgDiv.innerHTML = `<div class="message-bubble"><small>FinSec AI is analyzing...</small></div>`;
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function formatBotResponse(text) {
        if (!text) return "";
        return text
            .split("\n\n")
            .map(para => `<p>${escapeHtml(para).replace(/\n/g, "<br>")}</p>`)
            .join("");
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    return {
        init,
        sendMessage,
    };
})();
