import json
import os
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional
from langchain_core.memory import BaseMemory
from pydantic import Field




class AgentMemory(BaseMemory):
    max_turns: int = Field(default=20)
    save_path: str = Field(default="agent_memory.json")
    interactions: Dict[str, deque] = Field(default_factory=lambda: defaultdict(lambda: deque(maxlen=20)))
    context: Dict[str, dict] = Field(default_factory=lambda: defaultdict(dict))


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load()


    # Zorunlu property
    @property
    def memory_variables(self) -> List[str]:
        # LangChain LLM'e hangi key ile geçmişi vereceğini buradan öğrenir
        return ["chat_history", "agent_state"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        user_id = inputs.get("user_id", "default")
        history_str = self.get_recent_interactions(user_id, n=self.max_turns)
        agent_state = self.format_agent_state(user_id)
        return {"chat_history": history_str, "agent_state": agent_state}

    

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        user_id = inputs.get("user_id", "default")

        # Kullanıcıdan gelen metin için birkaç olası anahtar kontrolü
        human_message = inputs.get("input") or inputs.get("query") or inputs.get("prompt") or inputs.get("question") or ""

        # Model çıktısı farklı biçimlerde gelebilir: str veya dict
        ai_message = ""
        if isinstance(outputs, str):
            ai_message = outputs
        elif isinstance(outputs, dict):
            ai_message = (
                outputs.get("output")
                or outputs.get("text")
                or outputs.get("result")
                or outputs.get("response")
                or ""
            )
        else:
            ai_message = str(outputs)

        if human_message:
            self.add_interaction(user_id, role="human", message=human_message)
        if ai_message:
            # Eğer bir tool bilgisi varsa metadata ile kaydet
            if isinstance(outputs, dict) and outputs.get("tool"):
                self.add_interaction(user_id, role="ai", message=ai_message, type="tool", metadata={"tool": outputs.get("tool")})
                # opsiyonel: tool çıktısını ayrıca context'e ekle
                self.add_tool_output(user_id, outputs.get("tool"), outputs.get("tool_output", {}))
            else:
                self.add_interaction(user_id, role="ai", message=ai_message)

        # Durumu dosyaya yaz
        self.save()


    def clear(self) -> None:
        self.interactions.clear()
        self.context.clear()
        self.save()
    # ------------------------
    # Senin mevcut metodların (hiçbirini silmedim)
    # ------------------------
    def add_interaction(self, user_id: str, role: str, message: str, type="message", metadata=None):
        entry = {
            "role": role,
            "message": message,
            "type": type
        }
        if metadata:
            entry["metadata"] = metadata
        self.interactions[user_id].append(entry)
        self.save()

    def get_recent_interactions(self, user_id: str, n=5):
        recent = list(self.interactions[user_id])[-n:]
        return "\n".join([f"{item['role'].capitalize()}: {item['message']}" for item in recent])

    def get_interactions_by_tool(self, user_id: str, tool_name: str) -> List[Dict[str, Any]]:
        return [entry for entry in self.interactions[user_id] if entry.get("metadata", {}).get("tool") == tool_name]

    def has_used_tool(self, user_id: str, tool_name: str) -> bool:
        return any(self.get_interactions_by_tool(user_id, tool_name))

    def set_context(self, user_id: str, key: str, value):
        self.context[user_id][key] = value
        self.save()

    def get_context(self, user_id: str, key: str, default=None):
        return self.context[user_id].get(key, default)

    def clear_context(self, user_id: str):
        self.context[user_id].clear()
        self.save()
    
    def clear_intent(self, user_id: str):
        self.context[user_id]["current_intent"] = None
        self.context[user_id]["suspended_intents"] = []
        self.save()

    def set_last_successful_action(self, user_id: str, action_name: str):
        self.context[user_id]["last_action"] = action_name
        self.save()

    def get_last_successful_action(self, user_id: str) -> str:
        return self.context[user_id].get("last_action", "")
    
    def consume_last_successful_action(self, user_id: str) -> str:
        action = self.context[user_id].get("last_action", "")
        if "last_action" in self.context[user_id]:
            del self.context[user_id]["last_action"]
            self.save()
        return action

    def get_raw_interactions(self, user_id: str, n=10):
        return list(self.interactions[user_id])[-n:]

    def full_state(self, user_id: str):
        return {
            "recent_interactions": list(self.interactions[user_id]),
            "context": self.context[user_id]
        }

    def save(self):
        data = {
            "interactions": {
                uid: list(deque(messages, maxlen=self.max_turns))
                for uid, messages in self.interactions.items()
            },
            "context": dict(self.context)
        }
        with open(self.save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        raise ValueError("Empty file")
                    data = json.loads(content)
                    self.interactions = defaultdict(
                        lambda: deque(maxlen=self.max_turns),
                        {
                            uid: deque(messages, maxlen=self.max_turns)
                            for uid, messages in data.get("interactions", {}).items()
                        }
                    )
                    self.context = defaultdict(dict, data.get("context", {}))
            except (json.JSONDecodeError, ValueError):
                print(f"[WARN] Memory file '{self.save_path}' is empty or corrupted. Reinitializing.")
                self.interactions = defaultdict(lambda: deque(maxlen=self.max_turns))
                self.context = defaultdict(dict)

    def set_tool_chain(self, user_id: str, tool_chain: list):
        self.context[user_id]["pending_tool_chain"] = tool_chain
        self.save()

    def get_next_tool(self, user_id: str):
        chain = self.context[user_id].get("pending_tool_chain", [])
        if chain:
            next_tool = chain.pop(0)
            self.context[user_id]["pending_tool_chain"] = chain
            self.save()
            return next_tool
        return None

    def has_pending_tools(self, user_id: str):
        return bool(self.context[user_id].get("pending_tool_chain"))

    def clear_tool_chain(self, user_id: str):
        if "pending_tool_chain" in self.context[user_id]:
            del self.context[user_id]["pending_tool_chain"]
            self.save()

    def set_plan_info(self, user_id: str, plan_id: str, version: int):
        self.context[user_id]["plan_id"] = plan_id
        self.context[user_id]["plan_version"] = version
        self.save()

    def get_plan_info(self, user_id: str):
        return {
            "plan_id": self.context[user_id].get("plan_id"),
            "plan_version": self.context[user_id].get("plan_version"),
        }

    def add_tool_output(self, user_id: str, tool_name: str, output: dict):
        self.context[user_id].setdefault("tool_outputs", []).append({
            "tool": tool_name,
            "output": output
        })
        self.save()

    def get_context_tool_outputs(self, user_id: str):
        return self.context[user_id].get("tool_outputs", [])

    def has_suspended_chains(self, user_id: str) -> bool:
        return self.has_pending_tools(user_id)

    def find_keywords_in_history(self, user_id: str, keywords: List[str]) -> List[str]:
        matched = []
        for interaction in self.interactions[user_id]:
            for keyword in keywords:
                if keyword.lower() in interaction["message"].lower():
                    matched.append(keyword)
        return matched
    
    def get_recent_errors(self, user_id: str, n=3) -> List[str]:
        errors = [
            i["message"] for i in reversed(self.interactions[user_id])
            if i.get("type") == "tool_error"
        ]
        return errors[:n]

    def get_last_tool_error(self, user_id: str) -> str:
        for i in reversed(self.interactions[user_id]):
            if i.get("type") == "tool_error":
                return i["message"]
        return ""
    
    def get_tool_outputs(self, user_id: str) -> List[str]:
        return [
            i["message"]
            for i in self.interactions[user_id]
            if i.get("type") in ["tool", "tool_error"]
        ]

    def set_current_focus(self, user_id: str, focus: str):
        self.context[user_id]["current_focus"] = focus
        self.save()

    def get_current_focus(self, user_id: str):
        return self.context[user_id].get("current_focus", None)
    
    def suspend_current_intent(self, user_id: str):
        suspended = {
            "tool_chain": self.context[user_id].get("pending_tool_chain", []),
            "focus": self.context[user_id].get("current_focus"),
            "message": self.get_recent_interactions(user_id, 1),
        }
        if not suspended["tool_chain"]:
            print(f"[WARN] Tool chain bulunamadı, boş suspend ediliyor: {suspended}")
        
        self.context[user_id].setdefault("suspended_intents", []).append(suspended)
        self.context[user_id]["pending_tool_chain"] = []
        self.context[user_id]["current_focus"] = None
        self.save()

    def set_pending_intent(self, user_id, pending: dict):
        self.context.setdefault(user_id, {})
        self.context[user_id]["pending_intent"] = pending

    def get_pending_intent(self, user_id):
        return self.context.get(user_id, {}).get("pending_intent")

    def clear_pending_intent(self, user_id):
        if user_id in self.context and "pending_intent" in self.context[user_id]:
            self.context[user_id].pop("pending_intent", None)

    def resume_last_suspended(self, user_id: str):
        suspended_stack = self.context[user_id].get("suspended_intents", [])
        if suspended_stack:
            last = suspended_stack.pop()
            self.context[user_id]["pending_tool_chain"] = last.get("tool_chain", [])
            self.context[user_id]["current_focus"] = last.get("focus", None)
            # güncellenmiş stack'i geri yaz
            self.context[user_id]["suspended_intents"] = suspended_stack
            self.save()
            return {
                "tool_chain": last.get("tool_chain", []),
                "message": last.get("message", "Önceki görev devam ediyor."),
                "missing_parameters": [],
            }
        return None

    
    def get_agent_state(self, user_id: str) -> dict:
        ctx = self.context.get(user_id, {})
        state = {
            "current_intent": ctx.get("current_intent"),
            "current_focus": ctx.get("current_focus"),
            "pending_intent": ctx.get("pending_intent"),
            "pending_tool_chain": ctx.get("pending_tool_chain", []),
            "suspended_intents": ctx.get("suspended_intents", []),
            "completed_intents": ctx.get("completed_intents", []),
            "last_action": ctx.get("last_action"),
            "tool_outputs": ctx.get("tool_outputs", [])[-5:],  # son 5 tool çıktısı
        }
        return state

    def format_agent_state(self, user_id: str) -> str:
        try:
            return json.dumps(self.get_agent_state(user_id), ensure_ascii=False, indent=2)
        except Exception:
            return str(self.get_agent_state(user_id))
        
    def set_authenticated_user(self, session_key: str, user_id: str):
        """
        Belirli bir session_key (TC veya kullanıcı adı) için doğrulanmış user_id kaydeder.
        """
        self.set_context(session_key, "authenticated_user_id", user_id)
        self.save()

    def get_authenticated_user(self, session_key: str) -> Optional[str]:
        """
        Session key'e bağlı doğrulanmış user_id döner. Yoksa None.
        """
        return self.get_context(session_key, "authenticated_user_id")

    def clear_authenticated_user(self, session_key: str):
        """
        Session key için giriş bilgisini temizler.
        """
        ctx = self.context.get(session_key, {})
        if "authenticated_user_id" in ctx:
            del ctx["authenticated_user_id"]
            self.save()

    

memory = AgentMemory()