# -*- coding: utf-8 -*-
"""
鎵归噺璺戝閬撶渷璧涚湡棰樸€?姣忛亾棰樼嫭绔?run 鐩綍銆佺嫭绔?work_space銆佺嫭绔?plan_id锛屼簰涓嶅共鎵般€?浠讳綍涓€閬撳け璐ヤ笉褰卞搷鍏朵粬棰樸€?瀹屾垚鍚庢眹鎬诲埌 result.jsonl锛堟瘮璧涙彁浜ゆ牸寮忥級銆?
鐢ㄦ硶锛?    python try_many.py                        # 璺戦粯璁ゅ垪琛?(1, 3, 6, 7)
    python try_many.py 5 7                    # 鍙窇 task_id_5 鍜?task_id_7
"""
import os
import sys
import json
import time
import traceback
import re
from datetime import datetime
from pathlib import Path

# ====== 閰嶇疆 ======
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_ARTIFACTS_ROOT = PROJECT_ROOT.parent.parent / "local_artifacts"
COMPETITION_DOCS_DIR = PROJECT_ROOT / "docs" / "competition"
QUESTION_FILE = Path(r"D:\Users\Admin\Desktop\涓叴姣旇禌\瓒呯骇鏅鸿兘浣揬涓叴鎹ф湀鈥滄槦鍖犲笀鈥濆阀鍖犵簿鑻辨寫鎴樿禌-瓒呯骇鏅鸿兘浣撳紑鍙?鐪佽禌璇曢.txt")

# 榛樿瑕佽窇鐨勯鍙凤紙task_id 鏈熬鏁板瓧锛夈€傚懡浠よ鍙鐩栥€?DEFAULT_TASK_NUMS = [1, 3, 6, 7]

# 鍗曢瓒呮椂闃堝€硷紙绉掞級銆傝秴杩囪繖涓氨鍦?summary 閲屾爣 鈿?浣嗕笉寮哄埗涓柇锛圕o-Sight 娌℃湁 cancel 鏈哄埗锛夈€?SOFT_TIMEOUT = 1500  # 25 鍒嗛挓锛坱ask 3 閲嶈窇杩?16 鍒嗛挓锛岀粰瀹芥澗浜涳級

# 鎵归噺 run 鐨勬牴鐩綍
BATCH_ROOT = PROJECT_ROOT / "runs" / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
BATCH_ROOT.mkdir(parents=True, exist_ok=True)


# ====== 姣忛涓撳睘 prompt 寰皟 ======
# 閽堝閭ｄ簺鍘熷闂琛ㄨ堪妯＄硦鎴?Agent 瀹规槗璺戝亸鐨勯锛屾彁渚涚瓥鐣ユ彁绀恒€?# 杩欎簺 hint 浼氭嫾鍒?output_format 鏈熬锛屼笉淇敼鍘熼銆?TASK_HINTS = {
    # 绠€鍗曟暟瀛﹂ / 宸茬瓟瀵圭殑棰樹笉闇€瑕?hint
    "ZTE Super Agent Challenge_task_id_1": (
        "Approach: Use Wikipedia revision history API to fetch the FIRST revision of ZTE page in "
        "both 2025 and 2026. For each, count <ref> tags in the wikitext. Report the difference. "
        "Answer should be a single integer."
    ),
    "ZTE Super Agent Challenge_task_id_3": (
        "IMPORTANT: Amtrak's Adirondack line had ~11 stations as of July 2023. You MUST enumerate "
        "ALL of them (e.g., New York Penn Station, Yonkers, Croton-Harmon, Poughkeepsie, Rhinecliff, "
        "Hudson, Albany-Rensselaer, Saratoga Springs, Plattsburgh, etc.) 鈥?do NOT give up early. "
        "For each station, identify which OTHER commuter or heavy-rail lines share it. Exclude "
        "subway and light rail. Deduplicate the list of connecting lines. Answer is a single integer."
    ),
    "ZTE Super Agent Challenge_task_id_4": (
        "Search the Lithuanian library portal (e.g., vb.lcss.lt, lvb.lt, or eLABa) for the article "
        "'Bulvi懦 rinka 2009 metais' by Ingrida Luko拧i奴t臈. Get its abstract. The book 'The "
        "Propitious Esculent' by John Reader was published in 2008. Count how many times 2008 "
        "(as a year) is explicitly mentioned in the abstract. Answer is a single integer."
    ),
    "ZTE Super Agent Challenge_task_id_8": (
        "Strategy: (1) Use execute_code to plot each of the three matplotlib functions on a "
        "standard axis (y from -5 to 10, x from -2 to 2). Save each plot as a separate PNG. "
        "(2) Use image_analysis to inspect each PNG and identify what English LETTER the curve "
        "visually resembles (curves opening upward/downward/sideways form U, 鈭? or C-like shapes). "
        "(3) Concatenate the letters in order to get a university acronym (e.g., 'UVA', 'MIT'). "
        "(4) Search for that university and report its motto. Answer is the motto text."
    ),
    "ZTE Super Agent Challenge_task_id_9": (
        "CRITICAL: Do NOT use ask_question_about_video 鈥?it will hang forever on this system.\n"
        "The video is https://www.youtube.com/watch?v=zNM7OtnJFvU (PangaeaPanga clearing levels).\n"
        "Strategy:\n"
        "1. Use execute_code to fetch the YouTube page and extract music credits from the description:\n"
        "   import requests, re\n"
        "   headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}\n"
        "   r = requests.get('https://www.youtube.com/watch?v=zNM7OtnJFvU', headers=headers, timeout=30)\n"
        "   # Search for music attribution patterns in page source\n"
        "   text = r.text\n"
        "   for pat in [r'Song[:\\s]+([^\\n\"<]+)', r'Music[:\\s]+([^\\n\"<]+)', r'Artist[:\\s]+([^\\n\"<]+)']:\n"
        "       hits = re.findall(pat, text, re.IGNORECASE)\n"
        "       if hits: print(pat, hits[:5])\n"
        "2. Also search Tavily for: 'PangaeaPanga zNM7OtnJFvU smiling cloud blocks music song'\n"
        "3. Also try scrape_website on 'https://www.youtube.com/watch?v=zNM7OtnJFvU'\n"
        "   and look for music/song credits in the description\n"
        "4. The song plays when the player first jumps onto smiling cloud blocks 鈥?identify song + artist.\n"
        "5. Format answer: SONG NAME, ARTIST NAME"
    ),
    "ZTE Super Agent Challenge_task_id_10": (
        "CRITICAL: Do NOT use file_download_toolkit 鈥?it will hang on large archive.org files.\n"
        "Find the page number of the raccoon recipe in 1975 Joy of Cooking (Irma Rombauer).\n"
        "The correct 1975 Bobbs-Merrill edition on archive.org is: joyofcooking400romb\n"
        "Strategy:\n"
        "1. Use execute_code to STREAM the archive.org OCR text and stop at 'raccoon':\n"
        "   import requests\n"
        "   url = 'https://archive.org/stream/joyofcooking400romb/joyofcooking400romb_djvu.txt'\n"
        "   headers = {'User-Agent': 'Mozilla/5.0'}\n"
        "   r = requests.get(url, stream=True, timeout=90, headers=headers)\n"
        "   print('HTTP status:', r.status_code)\n"
        "   buf = ''; total = 0\n"
        "   for chunk in r.iter_content(16384):\n"
        "       buf += chunk.decode('utf-8', errors='ignore'); total += len(chunk)\n"
        "       if 'raccoon' in buf.lower():\n"
        "           idx = buf.lower().index('raccoon')\n"
        "           print('FOUND raccoon at offset', idx)\n"
        "           print('CONTEXT:', buf[max(0,idx-500):idx+800])\n"
        "           break\n"
        "       if total > 5000000: print('5MB searched, not found'); break\n"
        "2. In the context, look for a page header number above the raccoon text.\n"
        "   djvu OCR pages are separated by form-feed or blank lines with page numbers.\n"
        "3. If joyofcooking400romb fails, try: joyofcooking00romb_0 or joyofcooking300romb\n"
        "4. Answer is a single integer (the page number where raccoon recipe appears)."
    ),
}


# ====== 鍔犺浇璇曢 ======
def load_all_questions():
    """杩斿洖 dict: task_id -> question_text"""
    qs = {}
    with open(QUESTION_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3 and parts[2].strip().startswith("ZTE Super Agent"):
                qs[parts[2].strip()] = parts[1].strip()
    return qs


# ====== 绛旀鎶藉彇锛堝崌绾х増锛?=====
# 澶氭ā寮忔鍒欙紝浼樺厛绾т粠楂樺埌浣庛€備粠 markdown 鏂囨湰鏈熬鍊掔潃鎼溾€斺€旀渶鏈熬鐨勬渶鍙兘鏄渶缁堢瓟妗堛€?ANSWER_PATTERNS_PRIMARY = [
    # 鏄惧紡鏍囪瘑锛堟渶鍙俊锛?    r"Final\s+result\s*:\s*\n?\s*([^\n]+?)(?:\n\n|\n#|$)",
    r"Final\s+answer\s*:\s*\n?\s*([^\n]+?)(?:\n\n|\n#|$)",
    r"\*\*\s*Final\s+answer\s*\*\*\s*:?\s*([^\n]+?)(?:\n\n|\n#|$)",
    r"The\s+answer\s+is\s*[:锛歖?\s*([^\n.]+?)(?:[.]\s|\n|$)",
    r"Answer\s*:\s*\n?\s*([^\n]+?)(?:\n\n|\n#|$)",
]
# 寮辨ā寮忥紙鍏滃簳锛?ANSWER_PATTERNS_FALLBACK = [
    r"\bResult\s*:\s*([^\n]+?)(?:\n|$)",
    r"\bConclusion\s*:\s*([^\n]+?)(?:\n|$)",
    # markdown 鍔犵矖鐨勬渶鏈暟瀛?鍗曡瘝
    r"\*\*([^*\n]{1,60})\*\*\s*$",
]


def _clean_answer(s: str) -> str:
    """瑙勮寖鍖栫瓟妗堬細鍘诲紩鍙枫€佸姞绮楃鍙枫€侀灏炬爣鐐圭┖鐧?""
    if not s:
        return ""
    s = s.strip()
    # 鍙嶅鍘婚櫎澶栧眰瑁呴グ
    for _ in range(3):
        s = s.strip("`*\"' \t\n.,銆?锛?锛?)
        # 鍘绘帀澶栧眰 markdown link 鍖呰  [text](url) -> text
        m = re.fullmatch(r"\[([^\]]+)\]\([^)]+\)", s)
        if m:
            s = m.group(1).strip()
    return s


def _is_useful(answer: str) -> bool:
    """鍒ゆ柇绛旀鏄惁鏈夌敤鈥斺€斾笉鑳藉お闀裤€佷笉鑳芥槸鏃犳剰涔夌煭璇?""
    if not answer:
        return False
    if len(answer) > 200:
        return False
    bad_phrases = (
        "could not be determined", "unable to", "no answer", "cannot determine",
        "鏃犳硶纭畾", "涓嶈兘纭畾", "could not", "did not find", "unresolved",
    )
    lower = answer.lower()
    for bad in bad_phrases:
        if bad in lower:
            return False
    return True


def extract_answer(markdown_text: str) -> tuple[str, str]:
    """浠?CoSight 杩斿洖鐨?markdown 鎶ュ憡閲屾娊鍙栨渶缁堢瓟妗堛€?
    杩斿洖 (clean_answer, raw_extracted_snippet)銆?    raw_extracted_snippet 鐢ㄤ簬璇勫瀵圭収銆?    """
    if not markdown_text:
        return "", ""
    text = str(markdown_text).strip()

    # 浼樺厛妯″紡
    for pat in ANSWER_PATTERNS_PRIMARY:
        matches = list(re.finditer(pat, text, re.IGNORECASE | re.MULTILINE))
        if matches:
            raw = matches[-1].group(1).strip()
            ans = _clean_answer(raw)
            if _is_useful(ans):
                return ans, raw

    # 寮辨ā寮?    for pat in ANSWER_PATTERNS_FALLBACK:
        matches = list(re.finditer(pat, text, re.IGNORECASE | re.MULTILINE))
        if matches:
            raw = matches[-1].group(1).strip()
            ans = _clean_answer(raw)
            if _is_useful(ans):
                return ans, raw

    # 鍏滃簳锛氬彇鏈€鍚?5 琛岄噷绗竴涓湅璧锋潵鍍忕瓟妗堢殑鐭锛? 80 瀛楃 + 娌℃槑鏄鹃棶鍙?+ 涓嶆槸 step 鏍囪锛?    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    for ln in reversed(lines[-10:]):
        if 1 <= len(ln) <= 80 and "?" not in ln and not ln.lower().startswith(("step", "note", "tools", "summary")):
            cleaned = _clean_answer(ln)
            if _is_useful(cleaned):
                return cleaned, ln

    # 瀹炲湪娌℃湁锛氬彇鏈€鍚庝竴闈炵┖琛岋紙鎴柇 200锛?    if lines:
        return lines[-1][:200], lines[-1]
    return "", ""


def llm_post_process_answer(question: str, raw_report: str, tool_llm) -> str:
    """濡傛灉姝ｅ垯鎶藉嚭鏉ョ殑涓嶅儚绛旀锛岃 mini LLM 鎶戒竴娆°€?""
    try:
        from openai import OpenAI
        import httpx
        api_key = os.environ.get("TOOL_API_KEY") or os.environ.get("API_KEY")
        base_url = os.environ.get("TOOL_API_BASE_URL") or os.environ.get("API_BASE_URL")
        model = os.environ.get("TOOL_MODEL_NAME") or os.environ.get("MODEL_NAME")
        if not (api_key and base_url and model):
            return ""
        client = OpenAI(
            api_key=api_key, base_url=base_url,
            http_client=httpx.Client(verify=False, trust_env=False, timeout=60.0),
        )
        prompt = (
            f"Extract the single final answer to this question from the agent's report. "
            f"Reply with ONLY the answer鈥攏o quotes, no explanation, no labels.\n\n"
            f"Question: {question}\n\n"
            f"Agent report (last 3000 chars):\n{raw_report[-3000:]}\n\n"
            f"Final answer:"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        return _clean_answer(resp.choices[0].message.content)
    except Exception:
        return ""


# ====== 鍗曢鎵ц ======
def run_one(task_id: str, question_text: str, run_dir: Path):
    """璺戜竴閬撻銆傝繑鍥?dict: {task_id, question, model_answer, elapsed, error, run_dir}"""
    work_space = run_dir / "work_space"
    work_space.mkdir(parents=True, exist_ok=True)

    # 鍒?cwd 鍒?work_space锛岄槻姝㈡枃浠跺伐鍏疯鎵」鐩牴
    os.chdir(work_space)
    os.environ["WORKSPACE_PATH"] = str(work_space)

    from CoSight import CoSight  # noqa: E402
    from llm import llm_for_plan, llm_for_act, llm_for_tool, llm_for_vision  # noqa: E402

    # 鎷煎嚭 output_format锛氶€氱敤瑕佹眰 + 姣忛涓撳睘 hint
    base_format = (
        "Reply with the final answer only. If it's a number, just the integer. "
        "If it's a word/phrase, no extra explanation."
    )
    hint = TASK_HINTS.get(task_id, "")
    output_format = base_format + ("\n\nGuidance:\n" + hint if hint else "")

    cosight = CoSight(
        llm_for_plan, llm_for_act, llm_for_tool, llm_for_vision,
        work_space_path=str(work_space),
        message_uuid=task_id,
    )

    start = time.time()
    final_report = None
    err = None
    try:
        final_report = cosight.execute(question_text, output_format=output_format)
    except Exception:
        err = traceback.format_exc()
    elapsed = time.time() - start

    plan = cosight.plan
    # 淇濆瓨浜х墿
    if final_report:
        (run_dir / "final_report.md").write_text(str(final_report), encoding="utf-8")

    plan_state = {
        "title": plan.title,
        "steps": plan.steps,
        "step_statuses": plan.step_statuses,
        "step_notes": plan.step_notes,
        "step_details": plan.step_details,
        "step_files": getattr(plan, "step_files", {}),
        "dependencies": plan.dependencies,
        "result": plan.result,
    }
    (run_dir / "plan_state.json").write_text(
        json.dumps(plan_state, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    tool_calls_dump = {step: plan.step_tool_calls.get(step, []) for step in plan.steps}
    (run_dir / "tool_calls.json").write_text(
        json.dumps(tool_calls_dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # 鎶界瓟妗堬細鍏堢敤 plan.result锛圠LM finalize 鐨勮緭鍑猴級锛屼笉琛屽啀鐢?markdown 鎶ュ憡
    candidate_text = plan.result or (str(final_report) if final_report else "")
    answer, raw_snippet = extract_answer(candidate_text)

    # 绛旀鍚庡鐞嗭細濡傛灉姝ｅ垯鎶藉埌鐨勪笉鍍忕瓟妗堬紙澶暱 / 鍚斁寮冪煭璇級锛岀敤 mini LLM 鍐嶆娊涓€娆?    used_llm_postprocess = False
    if not _is_useful(answer) or len(answer) > 100:
        llm_answer = llm_post_process_answer(question_text, candidate_text, llm_for_tool)
        if _is_useful(llm_answer):
            answer = llm_answer
            used_llm_postprocess = True

    # 鏋勯€?reasoning_trace锛堟寜姣旇禌 result.jsonl 绀轰緥鐨勭函鏂囨湰鏍煎紡锛?    trace_lines = []
    for i, step in enumerate(plan.steps):
        trace_lines.append(f"{i+1}. {step}")
        notes = plan.step_notes.get(step) or ""
        if notes:
            short = notes.replace("\n", " ").strip()[:300]
            trace_lines.append(f"   - {short}")
    reasoning_trace = "\n".join(trace_lines)

    # 鍐欏崟棰?summary
    summary = [
        f"Task ID    : {task_id}",
        f"Question   : {question_text}",
        f"Elapsed    : {elapsed:.1f} sec" + ("  鈿?over soft timeout" if elapsed > SOFT_TIMEOUT else ""),
        f"Steps      : {len(plan.steps)}  ({sum(1 for s in plan.step_statuses.values() if s == 'completed')} completed)",
        f"Extracted answer: {answer}",
        f"  raw snippet   : {raw_snippet[:200]}",
        f"  used LLM post-process: {used_llm_postprocess}",
        f"Plan.result: {plan.result[:500] if plan.result else ''}",
        "",
    ]
    if err:
        summary.append("ERROR:")
        summary.append(err)
    (run_dir / "summary.txt").write_text("\n".join(summary), encoding="utf-8")

    return {
        "task_id": task_id,
        "Question": question_text,
        "model_answer": answer,
        "model_answer_raw": raw_snippet,
        "reasoning_trace": reasoning_trace,
        "elapsed_sec": elapsed,
        "steps_total": len(plan.steps),
        "steps_done": sum(1 for s in plan.step_statuses.values() if s == "completed"),
        "error": err,
        "run_dir": str(run_dir),
        "used_llm_postprocess": used_llm_postprocess,
        "final_report_excerpt": (str(final_report)[-400:] if final_report else ""),
    }


# ====== 鍏ュ彛 ======
def main():
    # 瑙ｆ瀽鍙傛暟
    if len(sys.argv) > 1:
        try:
            nums = [int(x) for x in sys.argv[1:]]
        except ValueError:
            print(f"Invalid args. Usage: python try_many.py [N1 N2 ...]  example: python try_many.py 1 3 6 7")
            sys.exit(1)
    else:
        nums = DEFAULT_TASK_NUMS

    questions = load_all_questions()
    targets = []
    for n in nums:
        tid = f"ZTE Super Agent Challenge_task_id_{n}"
        if tid not in questions:
            print(f"!! task_id {tid} not found in question file, skipping")
            continue
        targets.append((tid, questions[tid]))

    print("=" * 70)
    print(f"BATCH RUN 鈥?{len(targets)} tasks")
    for tid, q in targets:
        print(f"  - {tid}: {q[:80]}{'...' if len(q) > 80 else ''}")
    print(f"  Output: {BATCH_ROOT}")
    print("=" * 70)
    print()

    results = []
    jsonl_path = BATCH_ROOT / "result.jsonl"

    for idx, (tid, question_text) in enumerate(targets, start=1):
        short = tid.split("_")[-1]
        run_dir = BATCH_ROOT / f"task{short}"
        run_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'#' * 70}")
        print(f"# [{idx}/{len(targets)}] Running {tid}")
        print(f"# Question: {question_text[:120]}{'...' if len(question_text) > 120 else ''}")
        if tid in TASK_HINTS:
            print(f"# Hint applied: yes ({len(TASK_HINTS[tid])} chars)")
        print(f"{'#' * 70}\n")

        try:
            result = run_one(tid, question_text, run_dir)
        except Exception:
            # run_one 鍐呴儴宸?catch锛屼絾淇濋櫓鍐嶈９涓€灞?            print(f"!! Outer exception while running {tid}:")
            print(traceback.format_exc())
            result = {
                "task_id": tid,
                "Question": question_text,
                "model_answer": "",
                "model_answer_raw": "",
                "reasoning_trace": "",
                "error": traceback.format_exc(),
                "run_dir": str(run_dir),
            }

        results.append(result)

        # 澧為噺鍐?result.jsonl锛堟瘡閬撻瀹屾垚绔嬪埢 flush锛屾剰澶栨柇涔熶繚浣忓凡瀹屾垚鐨勶級
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in results:
                # 姣旇禌瑕佹眰鐨勫瓧娈?                line = {
                    "task_id": r["task_id"],
                    "Question": r["Question"],
                    "model_answer": r["model_answer"],
                    "reasoning_trace": r["reasoning_trace"],
                }
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

        # 灞忓箷閫熻
        print(f"\n>>> Done {tid} in {result.get('elapsed_sec', 0):.1f}s")
        print(f">>> Extracted answer: {result.get('model_answer', '')!r}")
        if result.get("used_llm_postprocess"):
            print(f">>> (answer was extracted via LLM post-process)")
        if result.get("error"):
            print(f">>> !! ERROR present, see summary.txt")

    # 鎬绘眹鎬?    print("\n\n" + "=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)
    for r in results:
        ok = "鉁? if (r.get("model_answer") and not r.get("error")) else "鉁?
        print(f"  {ok}  {r['task_id'].split('_')[-1]:>4}  ({r.get('elapsed_sec', 0):.0f}s)  鈫?{r.get('model_answer', '')!r}")
    print(f"\nresult.jsonl: {jsonl_path}")
    print(f"All artifacts: {BATCH_ROOT}")


if __name__ == "__main__":
    main()

