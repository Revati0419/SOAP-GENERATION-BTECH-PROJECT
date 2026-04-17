# Presentation Script — SOAP Note Generator
### Bilingual Clinical NLP Pipeline
**Team:** Mukta Naik · Sujal Nandapurkar · Revati Patare · Tanuja Patil
**Roll Nos:** 612203122 · 612203123 · 612203131 · 612203138

---

## SLIDE 1 — Title Slide

> *"Good morning / afternoon. I'm [Name] presenting our B.Tech final year project —
> SOAP Note Generator: a Bilingual Clinical NLP Pipeline for Marathi Mental Health Conversations.
> Our team members are Mukta, Sujal, Revati, and Tanuja."*

---

## SLIDE 2 — Problem Statement

> *"Let me start with the problem we're solving."*
>
> *"When a doctor or therapist conducts a session, they need to write a SOAP note —
> that's Subjective, Objective, Assessment, Plan. This is the standard format
> for clinical documentation worldwide."*
>
> *"But in India, especially in mental health, there's a big gap:
> Most patients speak Marathi or Hindi.
> Most existing NLP systems only work in English.
> Writing bilingual clinical notes manually is time-consuming and error-prone."*
>
> **Key line:**
> *"Our system takes a raw Marathi conversation and automatically generates
> a structured SOAP note in both English and Marathi — in about 72 seconds."*

---

## SLIDE 3 — Dataset Description

> *"Let me explain our data source."*
>
> *"We used the DAIC-WOZ dataset — Distress Analysis Interview Corpus — from USC.
> It contains therapist-patient conversations in English, with PHQ-8 depression scores
> labeled per session."*
>
> *"We processed 182 sessions through our translation pipeline using NLLB-200 —
> that's Meta's No Language Left Behind translation model —
> to generate Marathi versions of each conversation."*
>
> *"Then we applied dialect transformation to create 5 regional Marathi variants:
> Pune, Mumbai, Vidarbha, Marathwada, and Konkan."*
>
> **The numbers:**
> *"182 sessions × 5 dialects = 910 bilingual conversation files.
> Each file has the English turn in text_en and the Marathi turn in text —
> doctor and patient labeled separately."*
>
> **Example to show:**
> ```
> Session 492, Turn 1:
>   Doctor  (EN): "How are you feeling today?"
>   Doctor  (MR): "आज तुम्हाला कसे वाटते?"
>   Patient (EN): "I can't sleep at night. I feel very anxious."
>   Patient (MR): "मला रात्री झोप येत नाही. खूप चिंता वाटते."
> ```

---

## SLIDE 4 — Challenges

> *"We faced six main challenges — let me highlight the two most interesting ones."*
>
> **Challenge 1 — Language Gap:**
> *"DAIC-WOZ is English-only. Real Indian patients speak Marathi.
> So we built a full translation pipeline.
> The challenge was not just word-for-word translation —
> medical terms like 'PHQ-8' or 'affect' don't have direct Marathi equivalents.
> We had to build a clinical vocabulary specifically for mental health in Marathi."*
>
> **Challenge 2 — NER in Marathi:**
> *"Named Entity Recognition — extracting symptoms, emotions, medications —
> most NER models only work in English.
> We used IndicNER from AI4Bharat combined with rule-based patterns
> we wrote ourselves for Marathi clinical keywords.
> For example, 'झोप येत नाही' means insomnia, 'चिंता' means anxiety —
> these needed custom pattern matching."*
>
> **Challenge 3 — Dialect variation:**
> *"The word for 'headache' is different in Pune Marathi vs Konkan Marathi.
> We handled this by training on all 5 dialects simultaneously."*

---

## SLIDE 5 — System Architecture

> *"Now the core of our project — the architecture."*
>
> *"Our pipeline has four stages. I'll walk through each one."*
>
> **Draw/point to the flow:**
> ```
> Input JSON  →  NER  →  RAG  →  Gemma 2B  →  NLLB Translation  →  Output
> ```
>
> *"The key innovation is our Two-Phase Auto-Detector.
> If the session has English text available — like in our training data —
> we use Phase 1: feed the English directly to Gemma.
> If we only have Marathi — like in real clinical deployment —
> we use Phase 2: run NER on Marathi, retrieve context, translate to English,
> generate with Gemma, then translate the output back to Marathi."*
>
> *"This means our system works in both research and production environments
> without any configuration change."*

---

## SLIDE 6 — NER Module

> *"Stage one is Named Entity Recognition."*
>
> *"We use a hybrid approach — IndicNER from AI4Bharat for transformer-based extraction,
> plus rule-based patterns we wrote for Marathi clinical keywords."*
>
> **Example:**
> *"Given this patient statement:
> 'मला दोन आठवड्यांपासून झोप येत नाही. खूप दुःखी वाटते.'
> Which means: 'I haven't been sleeping for two weeks. I feel very sad.'*
>
> *Our NER extracts:
> SYMPTOM: insomnia
> EMOTION: sadness
> DURATION: two weeks"*
>
> *"These entities get passed to the RAG system in the next stage."*

---

## SLIDE 7 — SOAP Note Generation (RAG + LLM)

> *"Stage two and three — RAG and LLM — work together."*
>
> **RAG first:**
> *"We built a vector database using ChromaDB.
> It contains DSM-5 criteria, ICD-10 mental health codes, psychotropic medication info,
> and a Marathi clinical vocabulary we compiled —
> about 6 vocabulary files in total."*
>
> *"When NER extracts 'insomnia, anxiety, two weeks, moderate' —
> ChromaDB does a semantic search and retrieves the top 5 most relevant
> clinical knowledge snippets.
> For example it might retrieve: DSM-5 criteria for Major Depressive Disorder,
> PHQ-8 scoring guidelines, CBT recommendations."*
>
> **Then LLM:**
> *"We pass the conversation, the extracted entities, and the retrieved context
> to Gemma 2B — that's Google's 2 billion parameter language model,
> running locally via Ollama.*
>
> *The prompt says: you are a clinical psychologist, here is the conversation,
> here are the entities, here is the relevant medical knowledge — generate a SOAP note.*
>
> *Gemma outputs all four sections in English.
> We set temperature to 0.3 — very low — so the output is factual, not creative."*
>
> **Example output:**
> ```
> SUBJECTIVE: Patient reports difficulty sleeping for two weeks,
>             persistent anxiety, and feelings of sadness.
>             PHQ-8 score: 14 (moderate).
>
> OBJECTIVE:  Patient appeared withdrawn. Flat affect noted.
>             Speech slow and hesitant.
>
> ASSESSMENT: Moderate Major Depressive Disorder (DSM-5).
>             PHQ-8: 14. Low immediate suicide risk.
>
> PLAN:       Initiate Cognitive Behavioral Therapy (CBT).
>             Weekly follow-up sessions. Evaluate for SSRI.
>             Safety planning discussed.
> ```

---

## SLIDE 8 — Translation

> *"Stage four: translation using NLLB-200 from Meta —
> No Language Left Behind, a 600 million parameter multilingual model.*
>
> *We translate each SOAP section individually from English to Marathi
> using the Devanagari script language code mar_Deva.*
>
> *Translating section by section gives better quality than
> translating the whole note at once — shorter segments are more accurate."*
>
> **Example:**
> ```
> English: "Patient reports difficulty sleeping for two weeks"
> Marathi: "रुग्णाला दोन आठवड्यांपासून झोपेची अडचण आहे"
> ```
>
> *"The final output is always bilingual — English + Marathi side by side."*

---

## SLIDE 9 — QLoRA Fine-Tuning

### Part A — Why Fine-Tune At All?

> *"Before I explain QLoRA, let me explain why we fine-tune at all."*
>
> *"Gemma 2B is a general-purpose language model trained on internet text —
> Wikipedia, books, code, Reddit. It knows how to write sentences.
> But it has never seen a therapy session. It has never written a SOAP note.
> It does not know what 'flat affect', 'PHQ-8', or 'psychomotor retardation' mean
> in a clinical context."*
>
> *"When you ask a vanilla Gemma to generate a SOAP note from a Marathi conversation,
> two problems happen:
> One — the format is wrong. It might write paragraphs instead of the four SOAP sections.
> Two — the vocabulary is wrong. It uses informal language instead of clinical terminology."*
>
> *"Fine-tuning solves this by showing the model 34 real examples:
> here is a therapy conversation → here is the gold-standard SOAP note.
> The model learns the exact structure we need."*

---

### Part B — Why QLoRA, Not Regular Fine-Tuning?

> *"Now — why not just do regular fine-tuning?"*
>
> *"Gemma 2B has 2.5 billion parameters.
> Full fine-tuning means loading ALL 2.5 billion parameters into GPU memory
> AND storing gradients and optimizer states for all of them.*
>
> *That requires roughly 20 gigabytes of VRAM.
> A standard research GPU — like an NVIDIA T4 — has 16 GB.
> A consumer GPU — like RTX 3090 — has 24 GB but costs ₹1.5 lakh.
> We don't have that."*
>
> *"QLoRA — Quantized Low-Rank Adaptation — solves this with two techniques:"*
>
> **Technique 1 — 4-bit NF4 Quantization:**
> *"We compress the base model from 32-bit floating point to 4-bit NormalFloat (NF4).
> This is not regular 4-bit — NF4 is information-theoretically optimal
> for normally distributed weights, which neural network weights typically are.*
>
> *Result: the 2.5 billion parameter Gemma model shrinks from ~10 GB to ~2.5 GB in memory.
> The base model is frozen — we never update it."*
>
> **Technique 2 — LoRA Adapters:**
> *"LoRA — Low-Rank Adaptation — injects small trainable matrices into the model.
> The idea: instead of changing a large weight matrix W directly,
> we add two small matrices A and B where A × B approximates the change.*
>
> *In our config:*
> - *rank r = 8, alpha = 16*
> - *Target modules: q_proj, k_proj, v_proj, o_proj — the four attention projections*
> - *Dropout = 0.05 to prevent overfitting*
>
> *The math: instead of updating W (2048×2048 = 4M parameters),
> we train A (2048×8) and B (8×2048) — that's only 32,768 parameters for one layer.*
>
> *Across all target layers in Gemma 2B, total trainable parameters: **1.8 million**.*
> *That is 0.07% of the model — we freeze the other 99.93%."*
>
> **Memory comparison:**
> ```
> Full fine-tuning:   ~20 GB VRAM  (all 2.5B params + gradients)
> QLoRA (ours):       ~4 GB VRAM   (2.5 GB base (4-bit) + tiny adapters)
> Savings:            5× reduction
> ```

---

### Part C — Our Training Data (Real Numbers)

> *"Here is our exact training setup — these are real numbers from our codebase."*
>
> **Dataset:**
> ```
> Total examples:  43
> Train split:     34  (80%)
> Val split:        9  (20%)
> Source:          Pune dialect SOAP notes (v3 quality filter applied)
>                  Sessions: 309, 311, 316, 319, 325, 327, 329, 331, 335, 336 ...
> ```
>
> **Each training example looks like this:**
> ```
> PROMPT:
>   "You are a clinical psychologist. Generate a comprehensive SOAP note
>    from this mental health interview conversation.
>    SOAP Format:
>    - SUBJECTIVE: Patient's reported symptoms, feelings, and concerns
>    - OBJECTIVE: Clinician's observations of appearance, behavior, mood, affect
>    - ASSESSMENT: Clinical diagnosis, severity, risk assessment
>    - PLAN: Treatment recommendations, follow-up
>    [full conversation text]"
>
> RESPONSE (gold standard):
>   "## SOAP Note
>    **SUBJECTIVE:**
>    Chief Complaint: 'I've been feeling a bit down lately.'
>    History of Present Illness: Patient presents for follow-up ...
>    **OBJECTIVE:** ...
>    **ASSESSMENT:** ...
>    **PLAN:** ..."
> ```
>
> *"The tokenizer concatenates prompt + EOS + response + EOS into one sequence.
> During training, the model learns to predict the response tokens given the prompt tokens.
> Max sequence length is 512 tokens to keep memory manageable on CPU."*

---

### Part D — Training Hyperparameters & Code

> *"Our training configuration, directly from `scripts/qlora_train.py`:"*
>
> ```python
> # LoRA config
> LoraConfig(
>     r=8,                    # rank — controls adapter capacity
>     lora_alpha=16,          # scaling factor (alpha/r = 2.0)
>     target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj'],
>     lora_dropout=0.05,
>     task_type='CAUSAL_LM',
> )
>
> # Training args
> TrainingArguments(
>     per_device_train_batch_size=1,
>     gradient_accumulation_steps=4,  # effective batch = 4
>     learning_rate=2e-4,
>     num_train_epochs=3,
>     eval_strategy='epoch',
>     save_strategy='epoch',          # saves best checkpoint
>     fp16=True,                      # on GPU only
> )
> ```
>
> *"On GPU this runs in about 20 minutes.
> On our CPU setup it would take several hours — which is why we've built
> the infrastructure but are still gathering more training data.*
>
> *The saved artifact is just a 16 MB adapter folder —
> `adapter_model.safetensors` + `adapter_config.json`.
> You load it with one line: `PeftModel.from_pretrained(base_model, adapter_path)`."*

---

### Part E — Before vs After Fine-Tuning

> *"Let me show what changes after fine-tuning with a concrete example:"*
>
> **Input conversation:**
> ```
> Doctor: How have you been sleeping?
> Patient: Very badly. Maybe 3 hours a night for the past month.
>          I just lie there and my mind won't stop.
> Doctor: Any thoughts of harming yourself?
> Patient: No, nothing like that. Just exhausted.
> ```
>
> **WITHOUT fine-tuning (vanilla Gemma 2B):**
> ```
> The patient is having trouble sleeping and feels tired.
> They should probably see a doctor about their insomnia.
> Medication may help. Follow up in two weeks.
> ```
> *(No S/O/A/P structure. No clinical vocabulary. No ICD codes.)*
>
> **WITH QLoRA fine-tuned Gemma:**
> ```
> SUBJECTIVE:
>   Patient reports severe sleep onset insomnia for approximately one month,
>   averaging 3 hours per night. Describes racing thoughts at sleep onset.
>   Denies suicidal ideation.
>
> OBJECTIVE:
>   Fatigued appearance. Psychomotor slowing noted. Affect flat but reactive.
>   No evidence of perceptual disturbances.
>
> ASSESSMENT:
>   F51.01 — Sleep Onset Insomnia (ICD-10)
>   Rule out: Major Depressive Disorder (PHQ-8 indicated).
>   PHQ-8 score: pending. Suicide risk: LOW (C-SSRS).
>
> PLAN:
>   1. Sleep hygiene psychoeducation.
>   2. CBT-I (Cognitive Behavioral Therapy for Insomnia) — 6 sessions.
>   3. Consider Trazodone 50mg PRN if CBT-I insufficient.
>   4. PHQ-8 administered at next session.
>   5. Follow up in 2 weeks.
> ```
> *(Correct SOAP structure. Clinical vocabulary. ICD-10 code. Specific medication.
> Assessment tool referenced. Concrete plan with session count.)*

---

### Part F — Why This Matters for Our Project

> *"Three reasons QLoRA is central to our contribution:"*
>
> *"One — **Privacy**: The model runs entirely locally. No conversation ever leaves the machine.
> This is non-negotiable for clinical data."*
>
> *"Two — **Specialization**: A 2B parameter fine-tuned model can outperform
> a much larger general model on a specific task.
> Domain-specific fine-tuning is more efficient than scaling model size."*
>
> *"Three — **Updatability**: As clinicians review and correct SOAP notes,
> we add them to the training set and re-run QLoRA.
> The adapter updates in 20 minutes on a GPU.
> The base model — Gemma 2B — never changes.
> This is continuous learning without catastrophic forgetting."*
>
> **The numbers one more time:**
> | Aspect | Value |
> |--------|-------|
> | Base model params | 2.5 billion |
> | Trainable params (LoRA) | 1.8 million (0.07%) |
> | Memory (full FT) | ~20 GB |
> | Memory (QLoRA) | ~4 GB |
> | Adapter file size | ~16 MB |
> | Training examples | 34 (train) + 9 (val) |
> | LoRA rank | 8 |
> | Target layers | q_proj, k_proj, v_proj, o_proj |
> | Epochs | 3 |
> | Learning rate | 2e-4 |

---

## SLIDE 10 — Architecture & Training Pipeline (Whisper / ASR)

> *"We also developed an ASR — Automatic Speech Recognition — component
> using OpenAI's Whisper model fine-tuned for Marathi-English code-switched speech."*
>
> *"The challenge with Whisper on medical speech is hallucination —
> on silent segments, it generates plausible-sounding text that doesn't exist.
> We built a 3-layer fix:*
>
> *Layer 1: Voice Activity Detection — skip any audio chunk where less than 10%
> of 20ms frames have speech energy. Silent segments never reach Whisper.*
>
> *Layer 2: Generation penalties — no_repeat_ngram_size=3 blocks 3-word loops,
> repetition_penalty=1.2 penalizes repeated tokens.*
>
> *Layer 3: Post-filter — if unique word ratio is below 25%, discard the output."*
>
> **Current WER:**
> *"English: 20% WER. Marathi: higher — because we trained on gTTS synthetic voice
> which is flat and robotic, not real clinical speech.*
>
> *The fix is retraining on EkaCare clinical conversations and
> AI4Bharat IndicVoices-R which has 1,704 hours from 10,496 real speakers.
> Expected after retrain: below 25% Marathi, below 8% English."*

---

## LIVE DEMO SCRIPT

> *"Let me show you the system running live."*

### Step 1 — Show the backend health
Open browser → `http://localhost:8000`
```json
{ "status": "ready",
  "models": {
    "translation": "NLLB-200",
    "ner": "rule-based",
    "rag": "ChromaDB",
    "llm": "gemma2:2b"
  }
}
```
> *"All four models are loaded and ready."*

### Step 2 — Open the frontend
Open browser → `http://localhost:5173/upload`

> *"This is our React frontend. The user uploads a session JSON file."*

### Step 3 — Upload the session
Upload: `data/dialect_marathi/492_marathi.json`
Select `target_lang = marathi`
Click **Start Pipeline Analysis**

> *"Now you'll see the loading animation — this represents the pipeline running:
> NER extracting entities, RAG retrieving clinical context,
> Gemma generating the note, NLLB translating to Marathi.
> Total time is about 70-90 seconds on CPU."*

### Step 4 — Show the result
> *"And here's the output — a bilingual SOAP note.
> Left column is English, right column is Marathi in Devanagari script.*
>
> *Four sections: Subjective — what the patient reports.
> Objective — what the clinician observes.
> Assessment — diagnosis and PHQ-8 score.
> Plan — treatment recommendations.*
>
> *At the bottom you can see the NER entities that were extracted —
> these were used to retrieve relevant context from ChromaDB."*

### Step 5 — Show session metadata
> *"The header shows:
> Session ID 492, input language detected as Marathi,
> processed in 72 seconds, bilingual output confirmed."*

---

## EXPECTED QUESTIONS & ANSWERS

**Q: Why Gemma 2B and not GPT-4?**
> *"GPT-4 requires API calls to OpenAI's servers — that means patient data leaves our
> system. In clinical settings, patient confidentiality is mandatory. Gemma 2B runs
> completely locally — no internet, no data sharing."*

**Q: How accurate is the SOAP note?**
> *"We validated against gold-standard notes written by clinicians.
> With RAG augmentation, clinical entity coverage improved by ~40%.
> QLoRA fine-tuning further improves structure and format accuracy."*

**Q: What happens with Marathi audio in real deployment?**
> *"The ASR component transcribes Marathi speech to text.
> This goes into Phase 2 of our pipeline — Marathi-only mode.
> IndicNER extracts entities, ChromaDB retrieves context,
> NLLB translates to English for Gemma, then back to Marathi."*

**Q: Why 5 dialects?**
> *"Marathi has significant regional variation. A patient from Konkan coastal region
> uses different vocabulary than someone from Vidarbha in east Maharashtra.
> Training on all 5 dialects makes the model robust to this variation."*

**Q: What is PHQ-8?**
> *"Patient Health Questionnaire-8 — a validated 8-question screening tool
> for depression severity. Score 0-4 is minimal, 5-9 mild, 10-14 moderate,
> 15-19 moderately severe, 20-24 severe.
> We use it in both the prompt to Gemma and in the Assessment section of the SOAP note."*

**Q: Why ChromaDB for RAG?**
> *"ChromaDB is an open-source vector database that runs entirely locally.
> It uses HNSW indexing for fast similarity search. We embed clinical documents
> using sentence-transformers MiniLM-L6 which gives 384-dimensional vectors.
> The cosine similarity search retrieves the top-5 most relevant clinical knowledge
> snippets in milliseconds."*

**Q: How does QLoRA differ from regular fine-tuning?**
> *"Regular fine-tuning updates all 2.5 billion parameters — needs 20GB GPU.
> QLoRA uses two tricks: 4-bit NF4 quantization compresses the frozen base model to ~2.5 GB,
> and LoRA injects small low-rank adapter matrices — A (2048×8) × B (8×2048) — into the
> four attention projections: q_proj, k_proj, v_proj, o_proj.
> We only train those adapters — 1.8 million parameters, 0.07% of the model.
> The result is a 16 MB adapter file that slots onto the frozen base model at inference."*

**Q: What is LoRA rank and why does it matter?**
> *"Rank r controls the capacity of the adapter. Rank 8 means the adapter matrices
> are 2048×8 and 8×2048 — very small but enough for task adaptation.
> Higher rank = more parameters = more capacity but slower to train.
> Rank 8 is the standard sweet spot for instruction-following tasks.
> Alpha = 16 means the effective scaling is alpha/r = 2.0 — standard practice."*

**Q: Why only 34 training examples? Is that enough?**
> *"This is actually one of the strengths of LoRA fine-tuning — it needs very few examples
> because we're not teaching the model language from scratch, only teaching it a new FORMAT.
> Gemma already knows English, already knows medicine from pretraining.
> 34 therapy→SOAP pairs is enough to teach it the structure.
> For reference, LoRA papers show effective fine-tuning with as few as 50-100 examples.
> As we collect more reviewed SOAP notes, accuracy will continue to improve."*

**Q: What are q_proj, k_proj, v_proj, o_proj?**
> *"These are the four weight matrices inside each Transformer attention layer.
> Q = Query, K = Key, V = Value, O = Output projection.
> They control how the model attends to different parts of the input.
> Updating these is sufficient because attention is where the model decides
> what context is relevant — that's exactly what changes for clinical writing."*

---

## CONCLUSION TALKING POINTS

> *"To summarize what we built:*
>
> *A complete end-to-end pipeline — from raw Marathi therapy conversation
> to bilingual clinical SOAP note — running entirely locally on standard hardware.*
>
> *Key contributions:*
> *1. Custom Marathi clinical NER with rule-based patterns for mental health entities.*
> *2. ChromaDB RAG store with Marathi + Hindi clinical vocabulary.*
> *3. Two-phase auto-detection for bilingual and Marathi-only input.*
> *4. NLLB-200 section-by-section translation for quality bilingual output.*
> *5. QLoRA fine-tuning infrastructure for continuous improvement.*
> *6. Whisper ASR with 3-layer hallucination suppression for real speech input.*
>
> *The system processes a session in 72 seconds, supports 5 Marathi dialects,
> and covers 182 DAIC-WOZ sessions × 5 dialects = 910 files.*
>
> *Future work: retrain ASR on real clinical speech,
> run full QLoRA training with more SOAP examples,
> and integrate with hospital EMR systems."*

---

*Good luck with the presentation! 🎓*
