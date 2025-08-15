import json
import time
import argparse
import pandas as pd
from agent_runner import main  # memory, CURRENT_CONTEXT, run_supervisor kullanmıyoruz

def run_kpi_tests(scenario_file: str, rt_threshold: float = 5.0, fuzzy: bool = True):
    with open(scenario_file, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    results = []
    total = len(scenarios)

    def norm(s: str) -> str:
        return (s or "").strip().lower()

    for sc in scenarios:
        sc_id = sc.get("id", "NA")
        user_utterance = sc.get("user_utterance", "")
        print(f"\n=== {sc_id} | {user_utterance} ===")

        # Kullanıcı bağlamı
        context = dict(sc.get("mock_user_context", {}) or {})
        user_id_or_tc = context.get("user_id") or context.get("tc") or ""

        # Beklenenler
        exp = sc.get("expected_outcome", {}) or {}
        expected_success = bool(exp.get("should_succeed", True))
        expected_message = exp.get("final_assistant_message", "") or ""

        # Simülasyon
        start_time = time.time()
        try:
            step_result = main(user_id_or_tc, user_utterance)  # senin agent_runner.py
        except Exception as e:
            step_result = {"success": False, "response": f"[EXCEPTION] {e}"}
        elapsed = round(time.time() - start_time, 3)

        response_text = (step_result or {}).get("response", "") or ""
        success = bool((step_result or {}).get("success", False))

        # KPI’lar
        decision_accuracy = (expected_success == success)

        if fuzzy:
            message_match = norm(expected_message) in norm(response_text)
        else:
            message_match = expected_message in response_text

        response_time_ok = elapsed < rt_threshold
        passed = decision_accuracy and message_match and response_time_ok

        results.append({
            "id": sc_id,
            "decision_accuracy": decision_accuracy,
            "message_match": message_match,
            "response_time": elapsed,
            "passed": passed,
            "success": success,
            "response": response_text
        })

        print(f"Süre: {elapsed}s | "
              f"decision={decision_accuracy} | msg={message_match} | rt={response_time_ok} | ✅ {passed}")
        print(f"Reply: {response_text[:300]}")

    # Özet
    passed_count = sum(1 for r in results if r["passed"])
    print(f"\n=== KPI ÖZET ===\nBaşarılı: {passed_count}/{total}")

    # CSV kaydet
    df = pd.DataFrame(results)
    df.to_csv("kpi_results.csv", index=False)
    print("📄 Sonuçlar kpi_results.csv olarak kaydedildi.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="scenarios.json", help="Senaryo JSON dosyası")
    parser.add_argument("--rt", type=float, default=5.0, help="Yanıt süresi eşik (sn)")
    parser.add_argument("--no-fuzzy", action="store_true", help="Fuzzy mesaj eşleşmesini kapat")
    args = parser.parse_args()

    run_kpi_tests(
        scenario_file=args.file,
        rt_threshold=args.rt,
        fuzzy=not args.no_fuzzy
    )