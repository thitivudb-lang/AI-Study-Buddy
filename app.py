"""AI Study Buddy — Streamlit + Ollama (ออฟไลน์)
วางโน้ต/อัปโหลดไฟล์ -> สรุป แฟลชการ์ด ข้อสอบ ถามตอบ (RAG) และฟังเสียง
"""
import hashlib
import html
import io
import json
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import streamlit as st
import ollama
from typing import Literal

from pydantic import BaseModel

st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# =====================================================================
# ข้อความ 2 ภาษา (ไทย / English)
# =====================================================================
TX = {
    "th": {
        "app_sub": "เปลี่ยนโน้ต สไลด์ และ PDF ให้เป็นสรุป แฟลชการ์ด ข้อสอบ และผู้ช่วยถามตอบ",
        "step1": "วางโน้ตหรืออัปโหลดไฟล์",
        "step2": "สร้างชุดทบทวน",
        "step3": "ทบทวน ทำข้อสอบ ถามตอบ",
        "sb_opts": "ตัวเลือกการสร้าง",
        "out_lang": "ภาษาของเนื้อหาที่สร้าง",
        "lang_auto": "ตามภาษาของโน้ต",
        "lang_th": "ไทย",
        "lang_en": "English",
        "n_cards": "จำนวนแฟลชการ์ด",
        "n_quiz": "จำนวนข้อสอบ",
        "difficulty": "ระดับความยาก",
        "diff_easy": "ง่าย",
        "diff_medium": "ปานกลาง",
        "diff_hard": "ยาก",
        "adv": "ตั้งค่าขั้นสูง",
        "num_ctx": "ความจุบริบท (num_ctx) ยิ่งมากยิ่งอ่านโน้ตได้ยาว แต่กินหน่วยความจำการ์ดจอมากขึ้น",
        "ollama_down": "เชื่อมต่อ Ollama ไม่ได้ ตรวจว่าเปิดโปรแกรม Ollama อยู่ (ไอคอนรูปลามาที่มุมขวาล่างของแถบงาน) แล้วรีเฟรชหน้านี้",
        "model_missing": "ยังไม่ได้โหลดโมเดลเหล่านี้ใน Ollama: {names} เปิด PowerShell แล้วพิมพ์ ollama pull ตามด้วยชื่อโมเดล เช่น ollama pull {first}",
        "model_main": "โมเดลหลัก",
        "model_vision": "โมเดลอ่านรูป/PDF สแกน (ต้องมองเห็นภาพได้)",
        "model_fb": "โมเดลสำรอง (คั่นด้วยจุลภาค ลองตามลำดับเมื่อโควตาเต็มหรือเซิร์ฟเวอร์ยุ่ง)",
        "err_cooldown": "โมเดลทั้งหมดที่ตั้งไว้โควตาเต็มอยู่ ลองใหม่ได้ในอีกประมาณ {wait} หรือเพิ่มโมเดลสำรองในตั้งค่าขั้นสูง",
        "quota_wait": "โควตาจะกลับมาในอีกประมาณ {wait}",
        "q_title": "โควตา (ประมาณการ)",
        "q_ready": "พร้อมใช้",
        "q_full": "เต็ม",
        "q_used": "ใช้ไป {used} / {limit} ครั้ง เหลือประมาณ {rem}",
        "q_used_nolimit": "ใช้ไป {used} ครั้งวันนี้ (ยังไม่ทราบเพดาน)",
        "q_back": "ใช้ได้อีกใน {wait} (ประมาณ {time} น.)",
        "q_daily_reset": "รีเซ็ตรายวันใน {wait} (ประมาณ {time} น.)",
        "q_embed": "{model} (ถามตอบ): ใช้ไป {used} ครั้งวันนี้",
        "q_note": "ตัวเลขนี้ประมาณจากการนับในแอปนี้ และเพดานที่แอปเรียนรู้จากข้อความ error ของ Google ถ้าใช้ API key เดียวกันที่อื่น (เช่น AI Studio) ตัวเลขจริงจะเหลือน้อยกว่านี้ ดูตัวเลขจริงที่ aistudio.google.com/rate-limit โควตารายวันรีเซ็ตตอนเที่ยงคืนเวลาแปซิฟิก",
        "def_limit": "เพดานต่อวันที่สมมุติให้โมเดลที่ยังไม่ทราบ (0 = ไม่ทราบ)",
        "main_all_out": "โมเดลทั้งหมดโควตาเต็ม ใช้ได้อีกใน {wait} (ประมาณ {time} น.)",
        "main_using_fb": "โมเดลหลักเต็ม แอปกำลังใช้โมเดลสำรอง {model}",
        "main_line": "โควตาโมเดลหลัก: {status}",
        "cool_title": "โมเดลที่โควตาเต็ม",
        "cool_line": "{model}: ลองใหม่ได้ในอีก {wait}",
        "cool_retry": "ลองใหม่ทันที (ล้างสถานะ)",
        "wait_hm": "{h} ชม. {m} นาที",
        "wait_m": "{m} นาที",
        "wait_s": "{s} วินาที",
        "quota_waiting": "โควตาต่อนาทีเต็ม รอ {s} วินาทีแล้วลองใหม่อัตโนมัติ",
        "model_embed": "โมเดล embedding (สำหรับถามตอบ)",
        "adv_hint": "ดูโมเดลที่มีในเครื่องด้วยคำสั่ง ollama list ใน PowerShell",
        "usage": "เรียก API ในเซสชันนี้: {n} ครั้ง",
        "usage_hint": "ดูโควตาที่เหลือที่ aistudio.google.com/rate-limit",
        "notice_title": "ข้อควรรู้ก่อนใช้งาน",
        "notice_line": "ทำงานในเครื่องคุณทั้งหมด ข้อมูลไม่ถูกส่งออกอินเทอร์เน็ต แต่ AI อาจผิดพลาด ควรตรวจสอบกับต้นฉบับ",
        "notice_sidebar": "**การตั้งค่า** จำนวนข้อสอบ ภาษา และโมเดล อยู่ที่แถบด้านซ้าย (กดลูกศรมุมซ้ายบน)",
        "done": "สร้างชุดทบทวนเสร็จแล้ว",
        "notice_privacy": "**ความเป็นส่วนตัว** ใช้ Ollama รันในเครื่องคุณ เนื้อหาที่ใส่ไม่ถูกส่งไปที่ใดและใช้ได้โดยไม่ต้องต่ออินเทอร์เน็ต",
        "notice_ai": "**ความถูกต้อง** AI อาจตอบผิดหรือแต่งข้อมูลขึ้นเอง ควรเทียบกับเอกสารต้นฉบับก่อนนำไปสอบจริง",
        "notice_quota": "**ความเร็ว** ไม่มีโควตา แต่ความเร็วขึ้นกับเครื่อง การสร้างชุดทบทวนใช้เวลาประมาณหลายสิบวินาทีถึงสองสามนาที โน้ตที่ยาวเกินจะถูกตัดตามค่า num_ctx",
        "notice_pdf": "**ไฟล์** อ่านได้ทั้ง PDF, Word, PowerPoint และรูปภาพ ถ้า PDF ถอดข้อความแล้วเพี้ยนหรือเป็นภาพสแกน ระบบจะให้โมเดลอ่านเป็นภาพทีละหน้า (ช้ากว่า และแม่นน้อยกว่าโมเดลบนคลาวด์)",
        "notice_short": "AI อาจผิดพลาด ควรตรวจสอบกับเอกสารต้นฉบับก่อนนำไปใช้จริง",
        "upload_label": "อัปโหลดไฟล์ PDF, Word, PowerPoint, รูปภาพ, txt หรือ md (เลือกได้หลายไฟล์)",
        "read_mode": "วิธีอ่านไฟล์",
        "read_auto": "อัตโนมัติ (ให้ AI ช่วยเฉพาะหน้าสแกน/หน้าที่ข้อความเพี้ยน)",
        "read_fast": "แบบปกติ (เร็วที่สุด)",
        "read_ai": "ให้ AI อ่านทุก PDF (แม่นที่สุด แต่ช้า)",
        "read_hint": "AI อ่านได้แม้ PDF ที่สแกนหรือฟอนต์ไทยเพี้ยน แต่ช้า อ่านทีละหน้า และอ่านสูงสุด 20 หน้าแรกต่อไฟล์",
        "upload_ai_used": "{name}: ให้ AI ช่วยอ่านหน้าสแกน/หน้าที่ข้อความเพี้ยน {n} ครั้ง (หน้าอื่นใช้ข้อความจริงในไฟล์) ควรอ่านทวนอีกรอบ",
        "upload_ai_fail": "{name}: ให้ AI อ่านไม่สำเร็จ ({err}) ใช้ข้อความแบบปกติแทน",
        "upload_ai_cut": "{name}: ไฟล์ยาวมาก AI อ่านเฉพาะ {n} หน้าแรก",
        "upload_img_fast": "{name}: รูปภาพต้องให้ AI อ่าน เปลี่ยน “วิธีอ่านไฟล์” เป็นอัตโนมัติหรือให้ AI อ่าน",
        "upload_toolarge": "ไฟล์ใหญ่เกิน 18 MB",
        "upload_ok": "อ่านข้อความได้ {n:,} ตัวอักษรจาก {f} ไฟล์ ตรวจแก้ในช่องด้านล่างได้",
        "upload_fail": "อ่านไฟล์ {name} ไม่สำเร็จ: {err}",
        "upload_empty": "{name}: ไม่พบข้อความ (อาจเป็น PDF ที่สแกนเป็นรูปภาพ)",
        "upload_deduped": "{name}: พบข้อความซ้ำผิดปกติ ระบบตัดส่วนที่ซ้ำออกให้แล้ว",
        "upload_garbled": "{name}: ไฟล์นี้มีตัวอักษรที่อ่านไม่ออก {n} ตัว (มักเป็นสระ/วรรณยุกต์ไทยจากฟอนต์ในสไลด์ PDF) ระบบตัดออกให้แล้ว แต่คำอาจเพี้ยน ถ้าสำคัญให้ส่งออกเป็น Word หรือ txt แล้วอัปโหลดแทน",
        "notes_label": "โน้ตหรือเนื้อหาที่ต้องการทบทวน",
        "notes_ph": "วางโน้ตที่นี่ หรืออัปโหลดไฟล์ด้านบน",
        "samples": "ลองใช้ตัวอย่าง",
        "chars": "{n:,} ตัวอักษร",
        "too_short": "โน้ตสั้นเกินไป ใส่อย่างน้อย 50 ตัวอักษร",
        "slide_view": "ดูสไลด์/หน้าต้นฉบับ (เทียบกับข้อความที่ถอดได้)",
        "slide_file": "ไฟล์",
        "slide_page": "หน้า",
        "slide_fail": "แสดงหน้าต้นฉบับไม่ได้",
        "qz_study": "📖 ควรศึกษาที่สไลด์หน้า {p}",
        "fc_img_cap": "สไลด์หน้า {p}",
        "fc_ref": "อ้างอิงจากสไลด์หน้า {p}",
        "fc_view_slide": "ดูสไลด์หน้า {p}",
        "fc_ans_label": "พิมพ์คำตอบของคุณ แล้วกดตรวจ จึงจะพลิกการ์ดดูเฉลยได้",
        "fc_check": "ตรวจคำตอบ",
        "fc_skip": "ไม่รู้ ข้ามไปดูเฉลย",
        "fc_type_first": "พิมพ์คำตอบก่อน หรือกด \"ไม่รู้ ข้ามไปดูเฉลย\"",
        "fc_checking": "กำลังตรวจคำตอบ...",
        "fc_ok": "✅ ถูกต้อง",
        "fc_partial": "🟡 ถูกบางส่วน",
        "fc_bad": "❌ ยังไม่ถูก",
        "fc_unknown": "ตรวจอัตโนมัติไม่สำเร็จ ลองพลิกการ์ดแล้วเทียบกับเฉลยเอง",
        "fc_flip_help": "ตรวจคำตอบหรือกดข้ามก่อน จึงจะพลิกได้",
        "tone_warn": "ข้อความไทยที่โมเดลสร้างมีไม้เอก/ไม้โทหายไปมากผิดปกติ ลองกดสร้างใหม่ หรือเปลี่ยนโมเดลหลักในตั้งค่าขั้นสูง",
        "truncated": "โน้ตยาว {n:,} ตัวอักษร ส่วนสรุป แฟลชการ์ด และข้อสอบจะใช้ {m:,} ตัวอักษรแรก ส่วนถามตอบใช้ได้ทั้งหมด",
        "btn_generate": "สร้างชุดทบทวน",
        "btn_regen": "สร้างใหม่",
        "spin_gen": "กำลังสร้างชุดทบทวน",
        "spin_embed": "กำลังเตรียมระบบถามตอบ",
        "reused": "ใช้ชุดที่สร้างไว้แล้ว (กด “สร้างใหม่” ถ้าต้องการชุดใหม่)",
        "rag_unavailable": "สร้างชุดทบทวนสำเร็จ แต่เตรียมระบบถามตอบไม่สำเร็จ: {msg}",
        "rag_trunc": "โน้ตยาวมาก ระบบถามตอบใช้เฉพาะ {n} ส่วนแรก",
        "stat_cards": "แฟลชการ์ด {n} ใบ",
        "stat_quiz": "ข้อสอบ {n} ข้อ",
        "stat_chunks": "ค้นหาได้ {n} ส่วน",
        "tab_sum": "สรุป",
        "tab_cards": "แฟลชการ์ด",
        "tab_quiz": "ข้อสอบ",
        "tab_qa": "ถามตอบ",
        "listen": "ฟังสรุป",
        "tts_fail": "สร้างเสียงไม่สำเร็จ (ต้องเชื่อมต่ออินเทอร์เน็ต): {err}",
        "download": "ดาวน์โหลดชุดทบทวน (.md)",
        "card_of": "ใบที่ {i} จาก {n}",
        "flip": "พลิกการ์ด",
        "prev": "ก่อนหน้า",
        "next": "ถัดไป",
        "lbl_q": "คำถาม",
        "lbl_a": "คำตอบ",
        "no_cards": "ครั้งนี้ AI สร้างแฟลชการ์ดไม่สำเร็จ กด “สร้างใหม่” อีกครั้ง",
        "no_quiz": "ครั้งนี้ AI สร้างข้อสอบไม่สำเร็จ กด “สร้างใหม่” อีกครั้ง",
        "btn_check": "ตรวจคำตอบ",
        "btn_retry": "ทำใหม่",
        "unanswered": "คุณยังไม่ได้ตอบ {n} ข้อ (นับเป็นผิด)",
        "score": "คะแนน",
        "correct": "ถูก",
        "wrong": "ผิด เฉลย: {ans}",
        "quiz_q": "ข้อ {i}",
        "score_hi": "เยี่ยมมาก ทำได้ดีเลย",
        "score_mid": "ดีแล้ว ทบทวนอีกนิดจะแม่นขึ้น",
        "score_low": "ลองอ่านสรุปอีกรอบ แล้วกดทำใหม่",
        "ask_label": "ถามคำถามจากโน้ตของคุณ",
        "ask_ph": "เช่น วิธีแก้ overfitting มีอะไรบ้าง",
        "ask_btn": "ถาม",
        "mode_label": "แหล่งคำตอบ",
        "mode_notes": "เฉพาะที่ส่งมา",
        "mode_general": "ที่ส่งมา + AI วิเคราะห์เพิ่ม",
        "mode_web": "ที่ส่งมา + ค้นเว็บเพิ่ม",
        "hint_notes": "AI ตอบจากโน้ตและไฟล์ที่ส่งมาเท่านั้น ถ้าไม่มีข้อมูลจะบอกว่าไม่พบ",
        "hint_general": "คำตอบแยกเป็น 2 ส่วน คือ (1) จากที่ส่งมา และ (2) ที่ AI วิเคราะห์เพิ่มเติมจากความรู้ของมันเอง ส่วนที่สองควรตรวจสอบก่อนใช้",
        "hint_web": "เหมือนแบบกลาง แต่ส่วนเพิ่มเติมจะค้นข้อมูลจากเว็บด้วย (โควตาค้นเว็บจำกัดกว่า)",
        "sec_notes": "จากที่ส่งมา",
        "sec_notes_cap": "ตอบจากโน้ตและไฟล์ที่คุณส่งมาเท่านั้น",
        "sec_beyond": "เพิ่มเติมจาก AI (นอกเหนือจากที่ส่งมา)",
        "sec_beyond_cap": "ส่วนนี้ไม่ได้มาจากโน้ตของคุณ AI อาจผิดพลาด ควรตรวจสอบก่อนใช้",
        "sec_beyond_cap_web": "ส่วนนี้ไม่ได้มาจากโน้ตของคุณ มาจากการค้นเว็บและความรู้ของ AI ตรวจสอบแหล่งที่มาก่อนใช้",
        "src_notes": "จากโน้ตของคุณ",
        "src_general": "ไม่อยู่ในโน้ต ตอบจากความรู้ทั่วไปของ AI ควรตรวจสอบก่อนใช้",
        "src_mixed": "บางส่วนจากโน้ต บางส่วนจากความรู้ทั่วไปของ AI ควรตรวจสอบส่วนที่ไม่อยู่ในโน้ต",
        "src_web": "ค้นจากเว็บ ตรวจสอบแหล่งที่มาก่อนใช้",
        "web_sources": "แหล่งข้อมูลจากเว็บ",
        "ask_hint": "AI จะตอบจากเนื้อหาในโน้ตเท่านั้น ถ้าไม่มีข้อมูลจะบอกว่าไม่พบ",
        "sources": "ส่วนของโน้ตที่ใช้อ้างอิง",
        "cached": "คำตอบที่บันทึกไว้",
        "ask_clear": "ล้างประวัติ",
        "rag_off": "ระบบถามตอบยังไม่พร้อม กด “สร้างใหม่” เพื่อเตรียมอีกครั้ง",
        "not_found": "ไม่พบในโน้ต",
        "empty_title": "เริ่มต้นได้เลย",
        "empty_body": "วางโน้ตหรืออัปโหลดไฟล์ แล้วกด “สร้างชุดทบทวน” หรือกดตัวอย่างด้านบนเพื่อลองใช้",
        "setup_title": "ยังไม่ได้ตั้งค่า API key",
        "setup_body": "ขอ key ฟรีที่ aistudio.google.com/apikey แล้วใส่ในช่องด้านล่าง",
        "key_label": "Gemini API key",
        "key_save": "บันทึกและเริ่มใช้งาน",
        "key_remember": "จำ key นี้ไว้ในเครื่องนี้ (บันทึกลงไฟล์ .streamlit/secrets.toml ไม่ส่งให้ใคร)",
        "key_invalid": "key ต้องเป็นตัวอักษร ตัวเลข หรือเครื่องหมาย - _ . เท่านั้น ตรวจว่าคัดลอกมาครบและไม่มีช่องว่าง",
        "err_quota": "โควตาฟรีของโมเดลนี้หมดแล้ว (ต่อวันหรือต่อนาที) ลองรอสักครู่ หรือเพิ่มโมเดลสำรองในตั้งค่าขั้นสูง หรือเปิดการเรียกเก็บเงินใน Google AI Studio เพื่อเพิ่มโควตา",
        "err_busy": "Ollama ตอบกลับผิดพลาด (อาจหน่วยความจำไม่พอ) ลองลดค่า num_ctx ในตั้งค่าขั้นสูง หรือปิดโปรแกรมอื่นที่ใช้การ์ดจอ แล้วลองใหม่",
        "err_model": "ไม่พบโมเดลใน Ollama พิมพ์ ollama pull ตามด้วยชื่อโมเดลใน PowerShell หรือตรวจชื่อในตั้งค่าขั้นสูง",
        "err_key": "API key ใช้ไม่ได้ ตรวจไฟล์ secrets.toml ว่าใส่ถูกต้องและบันทึกแล้ว",
        "err_format": "AI ตอบกลับในรูปแบบที่อ่านไม่ได้ กดสร้างอีกครั้ง",
        "err_net": "เชื่อมต่อ Ollama ไม่ได้หรือใช้เวลานานเกินไป ตรวจว่าโปรแกรม Ollama เปิดอยู่แล้วลองใหม่",
        "err_generic": "เกิดข้อผิดพลาดที่ไม่คาดคิด",
        "err_details": "รายละเอียดทางเทคนิค",
        "footer": "สร้างด้วย Streamlit และ Ollama (ทำงานออฟไลน์) เพื่อการเรียนรู้",
    },
    "en": {
        "app_sub": "Turn your notes, slides and PDFs into a summary, flashcards, a quiz and a Q&A assistant.",
        "step1": "Paste notes or upload files",
        "step2": "Generate your study set",
        "step3": "Study, take the quiz, ask questions",
        "sb_opts": "Generation options",
        "out_lang": "Language of generated content",
        "lang_auto": "Same as notes",
        "lang_th": "Thai",
        "lang_en": "English",
        "n_cards": "Number of flashcards",
        "n_quiz": "Number of quiz questions",
        "difficulty": "Difficulty",
        "diff_easy": "Easy",
        "diff_medium": "Medium",
        "diff_hard": "Hard",
        "adv": "Advanced settings",
        "num_ctx": "Context size (num_ctx). Larger reads longer notes but uses more GPU memory.",
        "ollama_down": "Cannot reach Ollama. Make sure the Ollama app is running (llama icon in the taskbar tray), then refresh this page.",
        "model_missing": "These models are not installed in Ollama: {names}. Open PowerShell and run ollama pull followed by the model name, e.g. ollama pull {first}",
        "model_main": "Main model",
        "model_vision": "Image/scanned-PDF reading model (must support vision)",
        "model_fb": "Fallback models (comma-separated, tried in order when quota is full or the server is busy)",
        "err_cooldown": "All configured models are out of quota. Try again in about {wait}, or add fallback models in Advanced settings.",
        "quota_wait": "Quota should come back in about {wait}",
        "q_title": "Quota (estimate)",
        "q_ready": "Ready",
        "q_full": "Full",
        "q_used": "Used {used} / {limit}, about {rem} left",
        "q_used_nolimit": "Used {used} today (limit unknown)",
        "q_back": "Available again in {wait} (about {time})",
        "q_daily_reset": "Daily reset in {wait} (about {time})",
        "q_embed": "{model} (Q&A): used {used} today",
        "q_note": "These numbers are estimated from the calls counted by this app and from limits it learned from Google's error messages. If the same API key is used elsewhere (e.g. AI Studio), the real remainder is lower. See actual figures at aistudio.google.com/rate-limit. The daily quota resets at midnight Pacific Time.",
        "def_limit": "Assumed daily limit for models with an unknown limit (0 = unknown)",
        "main_all_out": "All models are out of quota. Available again in {wait} (about {time})",
        "main_using_fb": "The main model is full. The app is using fallback model {model}",
        "main_line": "Main model quota: {status}",
        "cool_title": "Models out of quota",
        "cool_line": "{model}: available again in {wait}",
        "cool_retry": "Retry now (clear status)",
        "wait_hm": "{h} h {m} min",
        "wait_m": "{m} min",
        "wait_s": "{s} s",
        "quota_waiting": "Per-minute quota reached. Waiting {s}s, then retrying automatically.",
        "model_embed": "Embedding model (for Q&A)",
        "adv_hint": "See installed models with the command ollama list in PowerShell",
        "usage": "API calls this session: {n}",
        "usage_hint": "Check remaining quota at aistudio.google.com/rate-limit",
        "notice_title": "Before you start",
        "notice_line": "Everything runs on your computer and nothing is sent over the internet. AI can still be wrong. Check against the original.",
        "notice_sidebar": "**Settings** Question counts, language and models are in the left sidebar (click the arrow at the top left).",
        "done": "Your study set is ready",
        "notice_privacy": "**Privacy** This uses Ollama running on your computer. Your content is not sent anywhere and no internet is needed.",
        "notice_ai": "**Accuracy** AI can be wrong or make things up. Check against your source material before relying on it for an exam.",
        "notice_quota": "**Speed** There is no quota, but speed depends on your hardware. A study set can take from tens of seconds to a few minutes. Notes that are too long are cut to fit num_ctx.",
        "notice_pdf": "**Files** PDF, Word, PowerPoint and images can be read. If a PDF's text comes out garbled or it is a scan, the model reads it page by page as images (slower and less accurate than cloud models).",
        "notice_short": "AI can make mistakes. Check against your source material before relying on it.",
        "upload_label": "Upload PDF, Word, PowerPoint, image, txt or md files (multiple allowed)",
        "read_mode": "How to read files",
        "read_auto": "Automatic (AI helps only with scanned/garbled pages)",
        "read_fast": "Standard (fastest)",
        "read_ai": "AI reads every PDF (most accurate, but slow)",
        "read_hint": "The AI can read scanned PDFs and PDFs with broken Thai fonts, but it is slow, reads page by page, and reads at most the first 20 pages per file.",
        "upload_ai_used": "{name}: AI helped read scanned/garbled pages ({n} call(s)). Other pages use the text in the file. Worth a quick check.",
        "upload_ai_fail": "{name}: the AI could not read it ({err}). Using standard extraction instead.",
        "upload_ai_cut": "{name}: very long file. The AI read only the first {n} pages.",
        "upload_img_fast": "{name}: images need the AI. Set “How to read files” to Automatic or AI.",
        "upload_toolarge": "File is larger than 18 MB",
        "upload_ok": "Read {n:,} characters from {f} file(s). You can edit the text below.",
        "upload_fail": "Could not read {name}: {err}",
        "upload_empty": "{name}: no text found (it may be a scanned PDF)",
        "upload_deduped": "{name}: unusual repeated text was found and the repeats were removed.",
        "upload_garbled": "{name}: {n} unreadable characters were found (often Thai vowels or tone marks from fonts embedded in slide PDFs). They were removed, but some words may look wrong. If it matters, export the file as Word or txt and upload that instead.",
        "notes_label": "Notes or content to review",
        "notes_ph": "Paste your notes here, or upload files above",
        "samples": "Try an example",
        "chars": "{n:,} characters",
        "too_short": "Notes are too short. Enter at least 50 characters.",
        "slide_view": "View original slides/pages (compare with extracted text)",
        "slide_file": "File",
        "slide_page": "Page",
        "slide_fail": "Could not show the original page",
        "qz_study": "📖 Study this at slide {p}",
        "fc_img_cap": "Slide {p}",
        "fc_ref": "Based on slide {p}",
        "fc_view_slide": "View slide {p}",
        "fc_ans_label": "Type your answer, then check it to unlock the flip",
        "fc_check": "Check answer",
        "fc_skip": "I don't know, show the answer",
        "fc_type_first": "Type an answer first, or press \"I don't know, show the answer\"",
        "fc_checking": "Checking your answer...",
        "fc_ok": "✅ Correct",
        "fc_partial": "🟡 Partly correct",
        "fc_bad": "❌ Not quite",
        "fc_unknown": "Automatic check failed. Flip the card and compare with the answer yourself.",
        "fc_flip_help": "Check your answer or skip first to flip",
        "tone_warn": "The Thai text the model wrote is missing many tone marks. Try regenerating, or change the main model in Advanced settings.",
        "truncated": "Your notes are {n:,} characters. The summary, flashcards and quiz use the first {m:,}; Q&A can use all of it.",
        "btn_generate": "Generate study set",
        "btn_regen": "Regenerate",
        "spin_gen": "Generating your study set",
        "spin_embed": "Preparing the Q&A assistant",
        "reused": "Reused your existing set (press Regenerate for a new one)",
        "rag_unavailable": "Your study set is ready, but the Q&A assistant could not be prepared: {msg}",
        "rag_trunc": "Your notes are very long. Q&A uses only the first {n} sections.",
        "stat_cards": "{n} flashcards",
        "stat_quiz": "{n} quiz questions",
        "stat_chunks": "{n} searchable sections",
        "tab_sum": "Summary",
        "tab_cards": "Flashcards",
        "tab_quiz": "Quiz",
        "tab_qa": "Ask",
        "listen": "Listen to summary",
        "tts_fail": "Could not create audio (internet required): {err}",
        "download": "Download study set (.md)",
        "card_of": "Card {i} of {n}",
        "flip": "Flip card",
        "prev": "Previous",
        "next": "Next",
        "lbl_q": "Question",
        "lbl_a": "Answer",
        "no_cards": "The AI could not create flashcards this time. Press Regenerate.",
        "no_quiz": "The AI could not create a quiz this time. Press Regenerate.",
        "btn_check": "Check answers",
        "btn_retry": "Try again",
        "unanswered": "{n} question(s) unanswered (counted as wrong)",
        "score": "Score",
        "correct": "Correct",
        "wrong": "Wrong. Answer: {ans}",
        "quiz_q": "Question {i}",
        "score_hi": "Excellent work",
        "score_mid": "Good. A little more review will help",
        "score_low": "Read the summary again, then try again",
        "ask_label": "Ask a question about your notes",
        "ask_ph": "e.g. How can I reduce overfitting?",
        "ask_btn": "Ask",
        "mode_label": "Answer source",
        "mode_notes": "Only what I sent",
        "mode_general": "What I sent + AI analysis",
        "mode_web": "What I sent + web search",
        "hint_notes": "The AI answers only from the notes and files you sent. If the answer is not there, it says so.",
        "hint_general": "Answers come in two parts: (1) from what you sent and (2) extra analysis from the AI's own knowledge. Verify the second part before relying on it.",
        "hint_web": "Same as the middle option, but the extra part also searches the web (the web search quota is tighter).",
        "sec_notes": "From what you sent",
        "sec_notes_cap": "Answered only from your notes and files",
        "sec_beyond": "Extra from the AI (beyond what you sent)",
        "sec_beyond_cap": "This part is not from your notes. The AI can be wrong, so verify before relying on it.",
        "sec_beyond_cap_web": "This part is not from your notes. It comes from web search and the AI's knowledge. Check the sources before relying on it.",
        "src_notes": "From your notes",
        "src_general": "Not in your notes. Answered from the AI's general knowledge. Verify before relying on it.",
        "src_mixed": "Partly from your notes, partly from the AI's general knowledge. Verify the parts not in your notes.",
        "src_web": "Found by web search. Check the sources before relying on it.",
        "web_sources": "Web sources",
        "ask_hint": "The AI answers only from your notes. If the answer is not there, it says so.",
        "sources": "Parts of your notes used as sources",
        "cached": "Saved answer",
        "ask_clear": "Clear history",
        "rag_off": "The Q&A assistant is not ready. Press Regenerate to prepare it again.",
        "not_found": "Not found in the notes",
        "empty_title": "Get started",
        "empty_body": "Paste notes or upload a file, then press “Generate study set”. Or try one of the examples above.",
        "setup_title": "API key not set",
        "setup_body": "Get a free key at aistudio.google.com/apikey and paste it below.",
        "key_label": "Gemini API key",
        "key_save": "Save and start",
        "key_remember": "Remember this key on this computer (saved to .streamlit/secrets.toml, shared with no one)",
        "key_invalid": "A key may only contain letters, digits and - _ . Check that you copied all of it with no spaces.",
        "err_quota": "The free quota for this model is used up (daily or per minute). Wait a while, add fallback models in Advanced settings, or enable billing in Google AI Studio for higher limits.",
        "err_busy": "Ollama returned an error (possibly out of memory). Lower num_ctx in Advanced settings, close other apps that use the GPU, and try again.",
        "err_model": "The model was not found in Ollama. Run ollama pull followed by the model name in PowerShell, or check the name in Advanced settings.",
        "err_key": "The API key does not work. Check that secrets.toml is correct and saved.",
        "err_format": "The AI replied in a format that could not be read. Try generating again.",
        "err_net": "Cannot reach Ollama or it took too long. Make sure the Ollama app is running and try again.",
        "err_generic": "Something unexpected went wrong",
        "err_details": "Technical details",
        "footer": "Built with Streamlit and Ollama (offline) for learning",
    },
}

SAMPLES = {
    "Overfitting": {
        "th": "Overfitting คือภาวะที่โมเดลเรียนรู้ข้อมูลฝึกสอนได้ดีเกินไป จนจำแม้กระทั่งสัญญาณรบกวน ทำให้ทำนายข้อมูลใหม่ได้แย่ ลักษณะคือ train accuracy สูงแต่ validation accuracy ต่ำ วิธีแก้ได้แก่ เพิ่มข้อมูลฝึกสอน ใช้ regularization เช่น L1 และ L2 ใช้ dropout ใน neural network และใช้ early stopping เพื่อหยุดฝึกก่อนที่โมเดลจะเริ่มจำข้อมูล",
        "en": "Overfitting happens when a model learns the training data too well, including its noise, so it predicts new data poorly. The typical sign is high training accuracy but low validation accuracy. Common fixes are collecting more training data, using regularization such as L1 and L2, using dropout in neural networks, and early stopping, which ends training before the model starts memorizing the data.",
    },
    "RAG": {
        "th": "Retrieval-Augmented Generation หรือ RAG คือเทคนิคที่ให้ LLM ค้นหาข้อมูลที่เกี่ยวข้องก่อนตอบ เพื่อลดการมั่วข้อมูล ขั้นตอนคือ แบ่งเอกสารเป็นชิ้นเล็กเรียกว่า chunking แปลงแต่ละชิ้นเป็นเวกเตอร์ด้วย embedding แล้วเก็บไว้ เมื่อผู้ใช้ถามคำถาม ระบบแปลงคำถามเป็นเวกเตอร์ แล้วหาชิ้นเอกสารที่คล้ายที่สุดด้วย cosine similarity จากนั้นนำชิ้นที่ได้ไปใส่ใน prompt พร้อมคำถามเพื่อให้ LLM ตอบโดยอ้างอิงจากเนื้อหานั้น ข้อดีคืออัปเดตความรู้ได้โดยไม่ต้องฝึกโมเดลใหม่ และตรวจสอบแหล่งที่มาของคำตอบได้",
        "en": "Retrieval-Augmented Generation (RAG) lets an LLM look up relevant information before answering, which reduces hallucination. First, documents are split into small pieces (chunking). Each piece is converted to a vector with an embedding model and stored. When a user asks a question, the question is also embedded and the most similar pieces are found with cosine similarity. Those pieces are placed in the prompt with the question so the LLM answers from that content. The benefits are that knowledge can be updated without retraining and answers can be traced to their sources.",
    },
    "CNN": {
        "th": "Convolutional Neural Network หรือ CNN เป็นโครงข่ายประสาทเทียมที่ออกแบบมาสำหรับข้อมูลภาพ ชั้น convolution ใช้ฟิลเตอร์ขนาดเล็กเลื่อนผ่านภาพเพื่อตรวจจับลักษณะ เช่น ขอบและรูปทรง ชั้น pooling ลดขนาดข้อมูลลงโดยเก็บค่าสำคัญไว้ เช่น max pooling เลือกค่าสูงสุดในแต่ละช่วง ทำให้คำนวณเร็วขึ้นและทนต่อการเลื่อนตำแหน่งของวัตถุ ชั้นท้ายเป็น fully connected layer ที่นำลักษณะที่ได้ไปจำแนกประเภทของภาพ ข้อดีของ CNN คือใช้พารามิเตอร์น้อยกว่าโครงข่ายแบบเชื่อมต่อทุกจุด เพราะฟิลเตอร์ตัวเดียวถูกใช้ซ้ำทั่วทั้งภาพ",
        "en": "A Convolutional Neural Network (CNN) is a neural network designed for image data. Convolution layers slide small filters over the image to detect features such as edges and shapes. Pooling layers shrink the data while keeping the important values; max pooling keeps the largest value in each region, which speeds up computation and tolerates small shifts of objects. The final fully connected layers use the extracted features to classify the image. A CNN needs far fewer parameters than a fully connected network because one filter is reused across the whole image.",
    },
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+Thai:wght@400;500;600&display=swap');
:root { --font:'Inter','Noto Sans Thai','Leelawadee UI','Leelawadee','Tahoma',system-ui,sans-serif;
        --line:rgba(127,127,127,.25); --soft:rgba(127,127,127,.07); --muted:rgba(127,127,127,.95);
        --ok:#16A34A; --bad:#DC2626; --blue:#2563EB; --amber:#D97706; }
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp textarea, .stApp input,
.stApp button, .stApp summary, .stApp [data-baseweb="select"] div, .stApp [data-baseweb="tab"],
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stMarkdownContainer"] { font-family:var(--font); }
.stApp pre, .stApp code, .stApp [data-testid="stText"] { font-family:var(--font), ui-monospace, Consolas, monospace; }
.stApp p, .stApp li, .stApp label { line-height:1.75; }
.block-container { max-width:760px; padding-top:2.4rem; padding-bottom:4rem; }
#MainMenu, footer, [data-testid="stDeployButton"], .stDeployButton { visibility:hidden; display:none; }
.brand { font-size:1.5rem; font-weight:600; line-height:1.3; margin:0; }
.tagline { color:var(--muted); font-size:.95rem; margin:.2rem 0 0 0; line-height:1.6; }
[data-testid="stHorizontalBlock"] [data-testid="stRadio"] label { font-size:.85rem; }
textarea { border-radius:12px !important; line-height:1.7 !important; }
[data-testid="stFileUploaderDropzone"] { border-radius:12px; border:1px dashed var(--line); background:transparent; }
.stButton > button, .stDownloadButton > button, [data-testid^="stBaseButton"] { border-radius:10px; font-weight:500; }
.stTabs [data-baseweb="tab-list"] { gap:1.4rem; border-bottom:1px solid var(--line); }
.stTabs [data-baseweb="tab"] { padding:.55rem 0; font-weight:500; background:transparent; }
.fcard { min-height:200px; display:flex; align-items:center; justify-content:center; text-align:center; padding:2rem 1.6rem;
         border:1px solid var(--line); border-radius:16px; font-size:1.3rem; line-height:1.75; background:var(--soft); margin:.6rem 0 1rem 0; }
.fcard.a { border-color:rgba(22,163,74,.55); }
.fcard small { display:block; font-size:.75rem; font-weight:500; color:var(--muted); margin-bottom:.5rem; }
.res { padding:.8rem 1rem; border:1px solid var(--line); border-radius:12px; margin:.5rem 0; }
.res.ok { border-left:3px solid var(--ok); }
.res.bad { border-left:3px solid var(--bad); }
.res .q { font-weight:500; margin-bottom:.2rem; }
.res .why { color:var(--muted); font-size:.9rem; margin-top:.25rem; }
.score { font-size:2.2rem; font-weight:600; line-height:1.3; }
.tag { display:inline-flex; align-items:center; gap:.45rem; font-size:.82rem; font-weight:600; margin-bottom:.3rem; }
.tag::before { content:""; width:.5rem; height:.5rem; border-radius:50%; background:var(--blue); }
.tag.b::before { background:var(--amber); }
[class*="st-key-ans_notes"] { border:1px solid var(--line); border-radius:12px; padding:1rem 1.1rem; margin-bottom:.6rem; }
[class*="st-key-ans_beyond"] { border:1px dashed var(--line); border-radius:12px; padding:1rem 1.1rem; margin-bottom:.6rem; background:var(--soft); }
@media (max-width:640px){ .brand{font-size:1.3rem;} .fcard{font-size:1.15rem; min-height:170px;} }
"""

# =====================================================================
# ภาษาหน้าเว็บ + CSS
# =====================================================================
st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)

def t(key: str, **kw) -> str:
    s = TX[st.session_state.get("lang", "th")][key]
    return s.format(**kw) if kw else s


def esc(x) -> str:
    return html.escape(str(x)).replace("\n", "<br>")


_h1, _h2 = st.columns([5, 2], vertical_alignment="center")
with _h2:
    st.radio(
        "Language",
        ["th", "en"],
        format_func=lambda c: {"th": "ไทย", "en": "English"}[c],
        horizontal=True,
        key="lang",
        label_visibility="collapsed",
    )
with _h1:
    st.markdown(
        f'<div class="brand">AI Study Buddy</div><div class="tagline">{esc(t("app_sub"))}</div>',
        unsafe_allow_html=True,
    )
st.write("")


# =====================================================================
# Ollama (รันในเครื่อง ไม่ต้องใช้ API key และไม่ต้องต่ออินเทอร์เน็ต)
# =====================================================================
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


@st.cache_resource
def get_client(host: str):
    return ollama.Client(host=host, timeout=900)


# =====================================================================
# แถบด้านข้าง
# =====================================================================
st.sidebar.markdown(f"### {t('sb_opts')}")
OUT_LANG = st.sidebar.selectbox(
    t("out_lang"), ["auto", "th", "en"], format_func=lambda c: t("lang_" + c), key="out_lang"
)
N_CARDS = st.sidebar.slider(t("n_cards"), 3, 10, 5, key="n_cards")
N_QUIZ = st.sidebar.slider(t("n_quiz"), 3, 10, 5, key="n_quiz")
DIFF = st.sidebar.selectbox(
    t("difficulty"), ["easy", "medium", "hard"], index=1, format_func=lambda c: t("diff_" + c), key="diff"
)
READ_MODE = st.sidebar.selectbox(
    t("read_mode"), ["auto", "fast", "ai"], format_func=lambda c: t("read_" + c), key="read_mode"
)
st.sidebar.caption(t("read_hint"))
with st.sidebar.expander(t("adv")):
    GEN_MODEL = st.text_input(t("model_main"), "qwen3:8b", key="gen_model").strip()
    VISION_MODEL = st.text_input(t("model_vision"), "qwen3-vl:4b", key="vision_model").strip()
    EMBED_MODEL = st.text_input(t("model_embed"), "bge-m3", key="embed_model").strip()
    NUM_CTX = int(st.select_slider(t("num_ctx"), options=[4096, 8192, 12288, 16384], value=8192, key="num_ctx"))
    st.caption(t("adv_hint"))

try:
    _installed = {m.model for m in get_client(OLLAMA_HOST).list().models}
except Exception:
    st.error(t("ollama_down"))
    st.stop()


def _norm(n: str) -> str:
    return n if ":" in n else n + ":latest"


_installed_norm = {_norm(i) for i in _installed}


def _has_model(name: str) -> bool:
    return _norm(name) in _installed_norm


_missing = [m for m in (GEN_MODEL, VISION_MODEL, EMBED_MODEL) if m and not _has_model(m)]
if _missing:
    st.warning(t("model_missing", names=", ".join(_missing), first=_missing[0]))

# =====================================================================
# ฟังก์ชันเรียก API + จัดการ error
# =====================================================================
MAX_CHARS = max(3000, int((NUM_CTX - 2500) * 1.8))   # ความยาวโน้ตที่ใช้สร้างสรุป/แฟลชการ์ด/ข้อสอบ (ขึ้นกับ num_ctx)
MAX_CHUNKS = 400    # จำนวนส่วนสูงสุดที่ใช้ในระบบถามตอบ


def classify_error(e: Exception) -> str:
    s = str(e)
    if isinstance(e, ollama.ResponseError):
        if e.status_code == 404:
            return "err_model"
        return "err_busy"
    if isinstance(e, (ConnectionError, TimeoutError)) or any(
        k in (type(e).__name__ + s) for k in ("Timeout", "ConnectError", "Failed to connect")
    ):
        return "err_net"
    if isinstance(e, (json.JSONDecodeError, ValueError)):
        return "err_format"
    return "err_generic"


def err_text(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"


def show_error(e: Exception):
    st.error(t(classify_error(e)))
    with st.expander(t("err_details")):
        st.code(err_text(e))


def gen_content(prompt: str, fmt=None, images=None, model=None, **opts) -> str:
    """เรียกโมเดลใน Ollama คืนข้อความตอบกลับ (fmt = JSON schema ถ้าต้องการให้ตอบเป็น JSON)"""
    msg = {"role": "user", "content": prompt}
    if images:
        msg["images"] = images
    kwargs = dict(
        model=model or (VISION_MODEL if images else GEN_MODEL),  # มีรูปแนบ = ใช้โมเดลอ่านภาพ
        messages=[msg],
        format=fmt,
        options={"num_ctx": NUM_CTX, "temperature": 0.3, "num_predict": 6144, **opts},  # num_predict = กันโมเดลวนเขียนไม่รู้จบ
    )
    client = get_client(OLLAMA_HOST)
    try:
        r = client.chat(think=False, **kwargs)  # ปิดโหมด "คิด" ของ qwen3: ไม่เปลืองโทเคน/เวลา และ JSON ไม่โดนตัดกลางคัน
    except TypeError:  # ไลบรารี ollama รุ่นเก่าไม่รู้จัก think
        r = client.chat(**kwargs)
    except Exception as e:
        if "think" not in str(e).lower():
            raise
        r = client.chat(**kwargs)  # โมเดลที่ไม่รองรับ think
    return (r.message.content or "").strip()


TONE_RULE = "When writing Thai, keep every tone mark (ไม้เอก ไม้โท ไม้ตรี ไม้จัตวา) and every vowel exactly; never drop them."


def low_tone(txt: str) -> bool:
    """ข้อความไทยที่ไม้เอก/โท/ตรี/จัตวาหายไป? ภาษาไทยปกติมีวรรณยุกต์ประมาณ 5-9% ของตัวอักษรไทย ต่ำกว่า 3% ถือว่าผิดปกติ"""
    thai = len(re.findall("[\u0E01-\u0E5B]", txt))
    if thai < 100:
        return False
    return len(re.findall("[\u0E48-\u0E4B]", txt)) / thai < 0.03


# =====================================================================
# สร้างชุดทบทวน
# =====================================================================
class Flashcard(BaseModel):
    q: str
    a: str
    page: int = 0   # หน้าสไลด์ที่การ์ดนี้อิงอยู่ (0 = ไม่ระบุ)
    file: str = ""  # ชื่อไฟล์ของหน้านั้น


class QuizItem(BaseModel):
    q: str
    choices: list[str]
    answer: int
    why: str
    page: int = 0          # หน้าสไลด์ที่ข้อนี้อิงอยู่ (0 = ไม่ระบุ)
    file: str = ""         # ชื่อไฟล์ของหน้านั้น
    figure: bool = False   # True = ต้องดูรูป/ตาราง/สูตรในสไลด์ประกอบการตอบ


class StudySet(BaseModel):
    summary: str
    flashcards: list[Flashcard]
    quiz: list[QuizItem]


def _nr(x) -> str:
    """ตัดข้อความวนซ้ำในผลลัพธ์จากโมเดล"""
    return collapse_repeats(str(x), 6, 3, False)[0]


# ---- แฟลชการ์ดอิงสไลด์: จับคู่การ์ดกับหน้าสไลด์ที่ตรงที่สุด + ตรวจคำตอบผู้เรียน ----
_FILE_RE = re.compile(r"^=== (.+?) ===\s*$")
_PAGE_RE = re.compile(r"^--- หน้า (\d+) ---\s*$")
_VISUAL_KEYS = ("[รูป —", "(สูตร —", "(ตาราง —")
MIN_GROUND = 0.12   # คะแนนความตรงขั้นต่ำ ต่ำกว่านี้ถือว่าการ์ดไม่ได้อิงสไลด์หน้าใดชัดเจน


def parse_pages(notes: str) -> list:
    """แยกโน้ตเป็นรายหน้าตามตัวคั่น '=== ไฟล์ ===' และ '--- หน้า N ---' (เฉพาะ PDF ที่ถอดด้วยแอปนี้)"""
    pages, cur_file, cur = [], "", None
    for ln in notes.split("\n"):
        m = _FILE_RE.match(ln)
        if m:
            cur_file, cur = m.group(1), None
            continue
        m = _PAGE_RE.match(ln)
        if m:
            cur = {"file": cur_file, "page": int(m.group(1)), "lines": []}
            pages.append(cur)
            continue
        if cur is not None:
            cur["lines"].append(ln)
    out = []
    for pg in pages:
        text = "\n".join(pg["lines"]).strip()
        out.append({"file": pg["file"], "page": pg["page"], "text": text, "visual": any(k in text for k in _VISUAL_KEYS)})
    return out


def _grams(txt: str) -> set:
    """ชุดตัวอักษร 3 ตัวติดกัน (ใช้ได้กับภาษาไทยที่ไม่มีเว้นวรรค) ตัดตัวบอกรูป/สูตรและเครื่องหมายออกก่อน"""
    t = re.sub(r"\(สูตร — [^)]*\)|\(ตาราง — [^)]*\)|\[รูป — [^\]]*\]", " ", txt.lower())
    t = re.sub(r"[\s|│#*_`\-–—:;,.!?()\[\]{}<>\"'/\\=+^]+", "", t)
    return {t[i:i + 3] for i in range(len(t) - 2)}


def ground_items(cards: list, notes: str, text_of) -> None:
    """ใส่ page/file/title/visual/ev ให้การ์ดหรือข้อสอบแต่ละรายการ โดยไม่เชื่อเลขหน้าที่โมเดลบอกอย่างเดียว:
    เทียบข้อความการ์ดกับข้อความของทุกหน้า (ให้น้ำหนักกลุ่มอักษรที่พบน้อยหน้ามากกว่า) แล้วเลือกหน้าที่ตรงที่สุด
    ถ้าหน้าที่โมเดลเลือกได้คะแนนใกล้เคียงหน้าที่ดีที่สุด (>= 80%) ใช้หน้าของโมเดล"""
    import math

    pages = parse_pages(notes)
    for c in cards:
        c.update({"visual": False, "ev": "", "title": ""})
    if not pages:
        for c in cards:
            c.update({"page": 0, "file": ""})
        return
    pg_grams = [_grams(p["text"]) for p in pages]
    title_grams = [_grams(_page_title(p["text"])) for p in pages]  # คำที่ตรงกับหัวข้อหน้า นับเป็นสองเท่า
    df = {}
    for gs in pg_grams:
        for g in gs:
            df[g] = df.get(g, 0) + 1
    n = len(pages)
    idf = lambda g: math.log(1 + n / df[g]) if g in df else math.log(1 + n)  # กลุ่มอักษรที่ไม่มีในโน้ตเลย = น้ำหนักสูงสุด (ดึงคะแนนลง)
    for c in cards:
        gs = _grams(text_of(c))
        total = sum(idf(g) for g in gs)
        if total <= 0:
            c.update({"page": 0, "file": ""})
            continue
        sc = [(sum(idf(g) for g in gs & pg) + sum(idf(g) for g in gs & tg)) / total for pg, tg in zip(pg_grams, title_grams)]
        best = max(range(n), key=sc.__getitem__)
        want_p, want_f = int(c.get("page") or 0), str(c.get("file") or "").lower()
        cand = [
            i for i, p in enumerate(pages)
            if want_p and p["page"] == want_p and (not want_f or want_f in p["file"].lower() or p["file"].lower() in want_f)
        ]
        pick = max(cand, key=sc.__getitem__) if cand else None
        chosen = pick if pick is not None and sc[pick] >= 0.8 * sc[best] else best
        if sc[chosen] < MIN_GROUND:
            c.update({"page": 0, "file": ""})
            continue
        p = pages[chosen]
        c.update({"page": p["page"], "file": p["file"], "visual": p["visual"], "ev": p["text"][:1500], "title": _page_title(p["text"])})


def _page_title(text: str) -> str:
    """หัวข้อของหน้า = บรรทัดแรกที่เป็นข้อความจริง (ไม่ใช่ตาราง/ตัวบอกรูป/เลขหน้า)"""
    for ln in text.split("\n"):
        ln = ln.strip()
        if len(ln) >= 3 and not ln.startswith(("|", "[", "(")) and not ln.isdigit():
            return ln[:70]
    return ""


def ground_cards(cards: list, notes: str) -> None:
    ground_items(cards, notes, lambda c: f'{c["q"]} {c["a"]}')


def ground_quiz(quiz: list, notes: str) -> None:
    ground_items(quiz, notes, lambda c: f'{c["q"]} {c["choices"][c["answer"]]} {c.get("why", "")}')


class FcJudge(BaseModel):
    verdict: Literal["correct", "partial", "incorrect"]
    feedback: str


def judge_answer(q: str, ref: str, user: str, ev: str) -> dict:
    """ให้โมเดลหลักตรวจคำตอบของผู้เรียนเทียบกับเฉลย (และข้อความในสไลด์) คืน {"verdict","feedback"}"""
    prompt = f"""You are a kind but accurate tutor checking a student's answer to a flashcard question.
QUESTION: {q}
REFERENCE ANSWER: {ref}
SLIDE TEXT (evidence, may be empty): {ev[:1500]}
STUDENT ANSWER: {user[:1200]}

Rules:
- Judge the meaning, not the wording, spelling or language. A different phrasing of the same idea is correct.
- verdict "correct": the key idea of the reference answer is there. "partial": some of it is right but an important part is missing or wrong. "incorrect": wrong, off-topic, empty, or only repeats the question.
- feedback: 1-2 short sentences in the same language as the question. Say what is right and what is missing or wrong, without copying the whole reference answer. Be encouraging.
- {TONE_RULE}
Return JSON only."""
    for _ in range(2):
        res = gen_content(prompt, FcJudge.model_json_schema(), temperature=0.1, num_predict=500)
        try:
            d = json.loads((res or "").replace("```json", "").replace("```", "").strip())
            v = str(d.get("verdict", "")).strip().lower()
            if v in ("correct", "partial", "incorrect"):
                return {"verdict": v, "feedback": _nr(d.get("feedback", ""))}
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    return {"verdict": "unknown", "feedback": ""}
# ---- จบส่วนแฟลชการ์ดอิงสไลด์ ----


def clean_study_set(d: dict) -> dict:
    """ตรวจโครงสร้างผลลัพธ์ ข้ามข้อที่ผิดรูปแบบแทนที่จะล่ม"""
    cards = []
    for c in d.get("flashcards") or []:
        q = c.get("q") or c.get("question")
        a = c.get("a") or c.get("answer")
        if q and a:
            try:
                pg = int(c.get("page") or 0)
            except (TypeError, ValueError):
                pg = 0
            cards.append({"q": _nr(q), "a": _nr(a), "page": pg, "file": str(c.get("file") or "")})
    quiz = []
    for it in d.get("quiz") or []:
        q = it.get("q") or it.get("question")
        ch = it.get("choices") or it.get("options") or it.get("choice")
        ans = it.get("answer")
        if isinstance(ans, str) and ans.strip().isdigit():
            ans = int(ans.strip())
        if q and isinstance(ch, list) and len(ch) >= 2 and isinstance(ans, int) and 0 <= ans < len(ch):
            try:
                pg = int(it.get("page") or 0)
            except (TypeError, ValueError):
                pg = 0
            quiz.append({
                "q": _nr(q), "choices": [str(x) for x in ch], "answer": ans, "why": _nr(it.get("why", "")),
                "page": pg, "file": str(it.get("file") or ""), "figure": bool(it.get("figure", False)),
            })
    return {"summary": _nr(d.get("summary", "")), "flashcards": cards, "quiz": quiz}


def shuffle_quiz(quiz: list, seed: str):
    """สลับตัวเลือก กันไม่ให้เฉลยกระจุกอยู่ข้อ ก/ข"""
    rnd = random.Random(seed)
    for it in quiz:
        correct = it["choices"][it["answer"]]
        rnd.shuffle(it["choices"])
        it["answer"] = it["choices"].index(correct)


def _study_prompt(notes: str, n_cards: int, n_quiz: int, diff_rule: str, lang_rule: str, avoid: str = "") -> str:
    avoid_rule = (
        f"\n- These items already exist. Do NOT repeat, reword or ask about the same thing as any of them:\n{avoid}" if avoid else ""
    )
    return f"""You are a study assistant. Create a study set from the notes below and return JSON matching the schema.
- summary: a clear summary of about 120-200 words. Short markdown bullet points are allowed.
- flashcards: exactly {n_cards} cards on the most important concepts (q = question or term, a = concise answer).
  Every card must be answerable from the content of one slide. Set "page" to the slide number from the "--- หน้า N ---" marker where the card's idea appears, and "file" to the file name from the "=== name ===" header above it (use page 0 and file "" if the notes have no such markers).
  Where a slide has a figure ([รูป …]), a table or a formula, make some cards ask about it (for example "จากภาพ/ตาราง/สูตรในสไลด์นี้ ...") and keep the other cards as normal text questions.
- quiz: exactly {n_quiz} multiple-choice questions with 4 choices each and exactly one correct choice. {diff_rule}
  Do not use "all of the above". "answer" is the 0-based index of the correct choice. "why" is a one-sentence explanation.
  Every question must be based on one slide: set "page" and "file" the same way as for the flashcards (page 0 and file "" if there are no markers).
  Set "figure" to true only when the student must look at that slide's figure, table or formula to decide the answer; then the question must say what to look at (for example "จากภาพ/ตาราง/สูตรในสไลด์นี้ ..."). Where the notes contain [รูป …], tables or formulas, make some questions figure-based and keep the rest text-only (figure false).
- Every flashcard and every quiz question must cover a DIFFERENT idea: no two items may ask about the same thing, even in different words, and no quiz question may repeat a flashcard.
- Use only information found in the notes.{avoid_rule}
- {lang_rule}
- {TONE_RULE}

NOTES:
{notes}"""


# ---- กันข้อซ้ำ: เทียบความคล้ายของการ์ด/ข้อสอบ ตัดข้อซ้ำออก แล้วขอเพิ่มข้อใหม่แทน ----
def _jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


_Q_FILLER = re.compile(
    r"คืออะไรบ้าง|คืออะไร|หมายถึงอะไร|มีอะไรบ้าง|ได้แก่|อธิบาย|what is|what are|define|explain|describe",
    re.I,
)


def _qgrams(q: str) -> set:
    """กลุ่มอักษรของคำถาม โดยตัดคำถามทั่วไป (คืออะไร/อธิบาย/what is) ออกก่อน ไม่งั้นคำถามคนละเรื่องจะดูคล้ายกันเพราะลงท้ายเหมือนกัน"""
    return _grams(_Q_FILLER.sub(" ", q))


def _similar(s1: tuple, s2: tuple) -> bool:
    """s = (กลุ่มอักษรของคำถาม, กลุ่มอักษรของคำตอบ) ถือว่าซ้ำเมื่อ: คำถามเกือบเหมือนกัน หรือคำถามคล้ายและคำตอบคล้าย
    (ถามเรื่องเดียวกันด้วยถ้อยคำต่างกัน) คำถามที่ต่างกันแค่คำเดียวแต่คำตอบคนละเรื่อง (เช่น ข้อดี/ข้อจำกัด) ไม่ถือว่าซ้ำ"""
    q, a = _jac(s1[0], s2[0]), _jac(s1[1], s2[1])
    return q >= 0.9 or (q >= 0.6 and a >= 0.25) or (a >= 0.5 and q >= 0.25) or (q >= 0.4 and a >= 0.4)


def _card_sig(c: dict) -> tuple:
    return (_qgrams(c["q"]), _grams(c["a"]))


def _quiz_sig(x: dict) -> tuple:
    return (_qgrams(x["q"]), _grams(x["choices"][x["answer"]]))


def dedupe_items(items: list, sig_of, seen: list | None = None):
    """ตัดรายการที่ซ้ำกับรายการก่อนหน้า (หรือกับ seen) คืน (รายการที่เหลือ, seen ที่อัปเดต)"""
    seen = list(seen or [])
    out = []
    for it in items:
        sg = sig_of(it)
        if any(_similar(sg, o) for o in seen):
            continue
        seen.append(sg)
        out.append(it)
    return out, seen


def fix_duplicates(data: dict, notes: str, n_cards: int, n_quiz: int, diff_rule: str, lang_rule: str) -> dict:
    """ตัดการ์ด/ข้อสอบที่ซ้ำกันเอง และข้อสอบที่ซ้ำกับการ์ด ถ้าเหลือไม่ครบจำนวน ขอโมเดลสร้างข้อใหม่ที่ไม่ซ้ำเพิ่มอีก 1 รอบ"""
    total_before = len(data["flashcards"]) + len(data["quiz"])
    cards, seen = dedupe_items(data["flashcards"], _card_sig)
    quiz, seen = dedupe_items(data["quiz"], _quiz_sig, seen)
    removed = total_before - len(cards) - len(quiz)  # จำนวนข้อซ้ำที่ตัดออก (ก่อนตัดให้เหลือตามที่ขอ)
    cards, quiz = cards[:n_cards], quiz[:n_quiz]
    need_c, need_q = n_cards - len(cards), n_quiz - len(quiz)
    if need_c > 0 or need_q > 0:
        avoid = "\n".join(["- " + c["q"][:120] for c in cards] + ["- " + x["q"][:120] for x in quiz])
        try:
            res = gen_content(
                _study_prompt(notes, max(need_c, 0), max(need_q, 0), diff_rule, lang_rule, avoid),
                StudySet.model_json_schema(),
            )
            more = clean_study_set(json.loads((res or "").replace("```json", "").replace("```", "").strip()))
            new_c, seen = dedupe_items(more["flashcards"], _card_sig, seen)
            new_q, seen = dedupe_items(more["quiz"], _quiz_sig, seen)
            cards += new_c[: max(need_c, 0)]
            quiz += new_q[: max(need_q, 0)]
        except Exception:  # ขอเพิ่มไม่ได้ก็ใช้เท่าที่มี ไม่ให้ทั้งชุดล่ม
            pass
    data["flashcards"], data["quiz"] = cards, quiz
    data["dup_removed"] = max(0, removed)
    return data


def generate_study_set(notes: str, n_cards: int, n_quiz: int, diff: str, out_lang: str, seed: str) -> dict:
    notes = notes[:MAX_CHARS]
    lang_rule = {
        "auto": "Write in the same language as the notes.",
        "th": "Write everything in Thai (keep technical terms in English where natural).",
        "en": "Write everything in English.",
    }[out_lang]
    diff_rule = {
        "easy": "Questions test recall of key facts and definitions.",
        "medium": "Questions mix recall with understanding.",
        "hard": "Questions test application and reasoning, with plausible distractors.",
    }[diff]
    prompt = _study_prompt(notes, n_cards, n_quiz, diff_rule, lang_rule)
    fmt = StudySet.model_json_schema()
    last = None
    for _ in range(2):  # ถ้า JSON พัง ลองอีกครั้ง
        res = gen_content(prompt, fmt)
        try:
            text = (res or "").replace("```json", "").replace("```", "").strip()
            data = clean_study_set(json.loads(text))
            data = fix_duplicates(data, notes, n_cards, n_quiz, diff_rule, lang_rule)  # ตัดข้อซ้ำ + ขอข้อใหม่แทน + ตัดให้เหลือตามจำนวนที่ขอ
            ground_cards(data["flashcards"], notes)  # เทียบการ์ดกับหน้าสไลด์จริง ไม่เชื่อเลขหน้าจากโมเดลอย่างเดียว
            shuffle_quiz(data["quiz"], seed)
            ground_quiz(data["quiz"], notes)  # หน้าสไลด์ที่ควรไปศึกษาของแต่ละข้อ (ตรวจกับข้อความจริง ไม่เชื่อโมเดลอย่างเดียว)
            if low_tone(data["summary"]):  # โหมด JSON ทำให้โมเดลเล็กทำวรรณยุกต์ไทยหล่น ลองเขียนสรุปใหม่เป็นข้อความธรรมดา
                alt_prompt = (
                    "Write a clear summary (about 120-200 words, short markdown bullet points allowed) of the notes below. "
                    f"Use only information found in the notes. {lang_rule} {TONE_RULE}\n\nNOTES:\n{notes}"
                )
                alt = _nr(gen_content(alt_prompt, repeat_penalty=1.1, num_predict=1200, temperature=0.2))
                if alt and not low_tone(alt):
                    data["summary"] = alt
            all_text = data["summary"] + " ".join(c["q"] + c["a"] for c in data["flashcards"]) + " ".join(q["q"] + "".join(q["choices"]) + q["why"] for q in data["quiz"])
            data["tone_warn"] = low_tone(all_text)
            return data
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            last = e
    raise last


# =====================================================================
# RAG (ถามตอบจากโน้ต)
# =====================================================================
def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    chunks, i = [], 0
    text = text.strip()
    while i < len(text):
        piece = text[i : i + size].strip()
        if piece:
            chunks.append(piece)
        i += size - overlap
    return chunks


def embed(texts: list[str], task: str) -> np.ndarray:
    client = get_client(OLLAMA_HOST)
    out = []
    for i in range(0, len(texts), 32):
        r = client.embed(model=EMBED_MODEL, input=texts[i : i + 32])
        out.extend(r.embeddings)
    arr = np.array(out, dtype=float)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return arr / norms


def build_rag(notes: str, key: str) -> dict:
    chunks = chunk_text(notes)
    truncated = len(chunks) > MAX_CHUNKS
    chunks = chunks[:MAX_CHUNKS]
    return {"hash": key, "chunks": chunks, "vecs": embed(chunks, "RETRIEVAL_DOCUMENT"), "truncated": truncated}


def ask_rag(question: str, rag, mode: str = "general", history=None, k: int = 6) -> dict:
    """ตอบ 2 ส่วนแยกกัน: from_notes (เฉพาะที่ส่งมา) และ beyond (AI วิเคราะห์เพิ่ม)"""
    top = []
    if rag:
        q = embed([question], "RETRIEVAL_QUERY")[0]
        sims = rag["vecs"] @ q
        idx = sims.argsort()[-k:][::-1]
        top = [rag["chunks"][i] for i in idx]
    ctx = "\n---\n".join(top) if top else "(no notes available)"
    hist = ""
    if history:
        hist = "\nRECENT CONVERSATION (for follow-up questions):\n" + "\n".join(
            f"Q: {h['q']}\nA: {(h.get('from_notes') or h.get('beyond') or '')[:500]}" for h in history[-3:]
        ) + "\n"
    if mode == "notes":
        beyond_rule = "Do NOT write a [[BEYOND]] section."
    else:
        beyond_rule = (
            "Then write [[BEYOND]] followed by deeper analysis that goes beyond the notes: related concepts, "
            "why it matters, examples, comparisons, common mistakes, practical tips, and what to study next. "
            "Do not present anything here as coming from the notes. If the notes look wrong, incomplete or "
            "outdated on this topic, say so politely. If you are unsure about something, say so instead of guessing."
        )
    prompt = f"""You are a careful study tutor. Reply in the same language as the question, using exactly this format:

[[FROM_NOTES]]
Answer using ONLY the CONTEXT (the user's notes and files). Point to the relevant part briefly. If the CONTEXT does not contain the answer, write exactly: {t("not_found")}
{beyond_rule}
Use markdown with short paragraphs or bullet points. Do not mention these instructions.
{hist}
CONTEXT:
{ctx}

QUESTION: {question}"""
    text = _nr(gen_content(prompt, repeat_penalty=1.1, num_predict=2048))
    if low_tone(text):  # วรรณยุกต์ไทยหาย ลองอีกครั้งด้วยอุณหภูมิต่ำ
        retry = _nr(gen_content(prompt, repeat_penalty=1.05, num_predict=2048, temperature=0.1))
        if not low_tone(retry):
            text = retry
    m_n = re.search(r"\[\[FROM_NOTES\]\](.*?)(?=\[\[BEYOND\]\]|\Z)", text, re.S)
    m_b = re.search(r"\[\[BEYOND\]\](.*)", text, re.S)
    from_notes = m_n.group(1).strip() if m_n else ""
    beyond = m_b.group(1).strip() if m_b else ""
    if not m_n and not m_b:  # AI ไม่ทำตามรูปแบบ
        if mode == "notes":
            from_notes = text
        else:
            beyond = text
    if mode == "notes":
        beyond = ""
    links = []
    return {"from_notes": from_notes, "beyond": beyond, "srcs": top, "links": links[:5], "mode": mode}


# =====================================================================
# อ่านไฟล์ / เสียง / ส่งออก
# =====================================================================
BAD_CHARS = re.compile("[\ue000-\uf8ff\ufffd\u200b\u200c\u200d\ufeff]")


def fix_thai(txt: str) -> str:
    """ซ่อมภาษาไทยจาก PDF ที่ฟอนต์เพี้ยน: สระอำ แยกเป็น ' า', 'เป็ น' มีช่องว่างแทรก, และ 'หน่ึง' สลับลำดับวรรณยุกต์"""
    txt = re.sub(r"(?<=[\u0E01-\u0E2E\u0E48-\u0E4B]) \u0E32", "\u0E33", txt)   # ส าคัญ -> สำคัญ, น้ า -> น้ำ
    txt = re.sub(r"(?<=\u0E47) (?=[\u0E01-\u0E2E])", "", txt)                      # เป็ น -> เป็น
    txt = re.sub(r"([\u0E48-\u0E4B])([\u0E34-\u0E37])", r"\2\1", txt)             # หน่ึง -> หนึ่ง
    return txt


_MATH_ALNUM = re.compile("[\U0001D400-\U0001D7FF\u210E]")
_MATH_GLYPHS = {"\u0DCD": "\u2211", "෍": "\u2211", "ቊ": "{", "ቐ": "{"}  # ฟอนต์สมการในสไลด์ map สัญลักษณ์ ∑ และ { ไปยังอักขระแปลกๆ


def fix_math(txt: str) -> str:
    """แปลงตัวอักษรคณิตศาสตร์แบบตัวเอียง/ตัวหนา (𝜔 𝑍 𝑘 𝓏) เป็นตัวธรรมดา (ω Z k z) ที่เบราว์เซอร์แสดงได้
    ทำทีละตัวเท่านั้น ห้ามใช้ NFKC กับทั้งข้อความ เพราะจะทำให้สระอำภาษาไทยแตกเป็นสองตัว"""
    import unicodedata

    txt = _MATH_ALNUM.sub(lambda m: unicodedata.normalize("NFKC", m.group(0)), txt)
    for a, b in _MATH_GLYPHS.items():
        txt = txt.replace(a, b)
    return txt


def clean_text(txt: str):
    """ตัดอักขระที่แสดงเป็นสี่เหลี่ยม (Private Use / replacement) และจัดรูปสระไทยให้เป็นมาตรฐาน"""
    import unicodedata

    bad = len(re.findall("[\ue000-\uf8ff\ufffd]", txt))
    txt = BAD_CHARS.sub("", txt)
    txt = fix_thai(txt)
    txt = fix_math(txt)
    txt = unicodedata.normalize("NFC", txt)
    return txt, bad


PAGE_IMG_MIN = 0.03   # รูปที่ใหญ่กว่า 3% ของหน้า ถึงจะนับว่าเป็น "รูป" (ไม่นับไอคอน/เส้นตกแต่ง)
PAGE_DRAWINGS_MIN = 60   # หน้าที่มีเส้น/รูปทรงเวกเตอร์เยอะมากโดยไม่มีรูป น่าจะเป็นกราฟ/แผนภาพ


BIG_OPS = "෍∑∏∫"   # ฟอนต์สมการบางตัว map ∑ เป็น ෍


_GREEK = re.compile("[\u0370-\u03FF]")


def line_text(spans: list) -> str:
    """รวมข้อความของบรรทัด ถ้าเป็นบรรทัดสมการ (มีอักษรคณิตศาสตร์/กรีก) ให้ใส่ตัวห้อย _{..} ตัวยก ^{..} ตามขนาดและตำแหน่งตัวอักษร"""
    plain = "".join(sp.get("text", "") for sp in spans)
    if not (_MATH_ALNUM.search(plain) or _GREEK.search(plain)):
        return plain.strip()
    real = [sp for sp in spans if sp.get("text", "").strip()]
    if not real:
        return plain.strip()
    big = max(sp.get("size", 0) for sp in real)
    ref = next((sp for sp in real if sp.get("size", 0) >= 0.95 * big), real[0])
    base = (ref.get("origin") or (0, 0))[1]
    out = []
    for sp in spans:
        t = sp.get("text", "")
        if t.strip() and big > 0 and sp.get("size", big) < 0.85 * big:
            up = (sp.get("origin") or (0, base))[1] < base - 0.2 * big
            out.append(("^{" if up else "_{") + t.strip() + "}")
        else:
            out.append(t)
    return "".join(out).strip()


def is_math(txt: str) -> bool:
    return bool(_MATH_ALNUM.search(txt) or _GREEK.search(txt) or any(c in txt for c in BIG_OPS) or "_{" in txt or "^{" in txt)


def attach_limits(lines: list) -> list:
    """สมการที่มีตัวห้อย/ตัวยกของ ∑ ∏ ∫ (เช่น 9 อยู่บน k=1 อยู่ล่าง) รวมเป็นบรรทัดเดียว: ∑_{k=1}^{9}"""
    lines = list(lines)
    drop = set()
    for idx, (y0, y1, x0, x1, txt) in enumerate(lines):
        op = next((c for c in txt if c in BIG_OPS), None)
        if op is None or idx in drop:
            continue
        h, cy = max(1.0, y1 - y0), (y0 + y1) / 2
        up = low = None
        for j, (a0, a1, b0, b1, t2) in enumerate(lines):
            if j == idx or j in drop or len(t2) > 14 or (a1 - a0) >= 0.9 * h or b1 < x0 or b0 > x1:
                continue
            c2 = (a0 + a1) / 2
            if cy - 2.2 * h <= c2 < cy - 0.15 * h and (up is None or c2 > (lines[up][0] + lines[up][1]) / 2):
                up = j
            elif cy + 0.15 * h < c2 <= cy + 2.2 * h and (low is None or c2 < (lines[low][0] + lines[low][1]) / 2):
                low = j
        if up is None and low is None:
            continue
        sym = "\u2211" if op in "෍∑" else op
        rep = sym + (("_{" + lines[low][4] + "}") if low is not None else "") + (("^{" + lines[up][4] + "}") if up is not None else "")
        lines[idx] = (y0, y1, x0, x1, txt.replace(op, rep, 1))
        drop.update(j for j in (up, low) if j is not None)
    return [ln for k, ln in enumerate(lines) if k not in drop]


def page_tables(page) -> list:
    """ตารางที่มีเส้นขอบ -> [(bbox, แถวของเซลล์)] ใช้ find_tables ของ PyMuPDF (รุ่นเก่าที่ไม่มี หรือหาไม่เจอ = ไม่มีตาราง)"""
    out = []
    try:
        for tb in page.find_tables().tables:
            rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in tb.extract()]
            cells = [c for r in rows for c in r]
            if len(rows) >= 2 and max(len(r) for r in rows) >= 2 and sum(1 for c in cells if c) >= len(cells) / 2:
                out.append((tb.bbox, rows))
    except Exception:
        pass
    return out


def page_layout_text(page, no: int):
    """ถอดข้อความของหน้า PDF ตามตำแหน่งจริงบนสไลด์ (บนลงล่าง ซ้ายไปขวา)
    ตารางที่มีเส้นขอบ -> แสดงเป็นตารางแบบ | a | b | แยกบล็อกต่อกัน
    ข้อความอื่นที่อยู่แถวเดียวกันแต่คนละช่อง/คอลัมน์ คั่นด้วย │
    ตัวห้อย/ตัวยกของ ∑ รวมเป็น ∑_{k=1}^{9}
    รูปภาพไม่พยายามอ่าน แต่ใส่ [รูป — ดูในสไลด์หน้า N] ไว้ตรงตำแหน่งที่รูปอยู่
    คืน (ข้อความพร้อมตัวบอกรูป, ข้อความล้วนไม่มีตัวบอกรูป)"""
    d = page.get_text("dict")
    tables = page_tables(page)

    def in_table(cx: float, cy: float) -> bool:
        return any(bx0 - 2 <= cx <= bx1 + 2 and by0 - 2 <= cy <= by1 + 2 for (bx0, by0, bx1, by1), _ in tables)

    lines = []  # (y0, y1, x0, x1, text)
    for b in d.get("blocks", []):
        if b.get("type") != 0:
            continue
        for ln in b.get("lines", []):
            txt = line_text(ln.get("spans", []))
            if txt:
                x0, y0, x1, y1 = ln["bbox"]
                if txt.isdigit() and len(txt) <= 3 and y0 > 0.9 * page.rect.height:
                    continue  # เลขหน้าของสไลด์ (มีตัวคั่น --- หน้า N --- อยู่แล้ว)
                if not in_table((x0 + x1) / 2, (y0 + y1) / 2):
                    lines.append((y0, y1, x0, x1, txt))
    lines = attach_limits(lines)
    marker = f"[รูป — ดูในสไลด์หน้า {no}]"
    note_math = f"(สูตร — อ่านยาก ควรเทียบกับสไลด์หน้า {no})"
    note_table = f"(ตาราง — ควรเทียบกับสไลด์หน้า {no})"
    pw, ph = page.rect.width, page.rect.height

    def build(with_images: bool) -> str:
        rows = []  # {"cy","h","items":[(x0,x1,text)],"fixed":bool}  fixed = ตาราง/รูป ไม่รวมกับแถวอื่น
        items = sorted(lines, key=lambda it: (it[0] + it[1]) / 2)
        for y0, y1, x0, x1, txt in items:
            cy, h = (y0 + y1) / 2, max(1.0, y1 - y0)
            if rows and not rows[-1]["fixed"] and abs(cy - rows[-1]["cy"]) <= 0.5 * min(h, rows[-1]["h"]):
                r = rows[-1]
                r["items"].append((x0, x1, txt))
                n = len(r["items"])
                r["cy"] = (r["cy"] * (n - 1) + cy) / n
                r["h"] = min(r["h"], h)
            else:
                rows.append({"cy": cy, "h": h, "items": [(x0, x1, txt)], "fixed": False})
        for (bx0, by0, bx1, by1), trows in tables:
            block = "\n" + "\n".join("| " + " | ".join(r) + " |" for r in trows) + ("\n" + note_table if with_images else "") + "\n"
            rows.append({"cy": by0, "h": 1.0, "items": [(bx0, bx1, block)], "fixed": True})
        if with_images:
            try:
                for im in page.get_image_info():
                    x0, y0, x1, y1 = im["bbox"]
                    if (x1 - x0) * (y1 - y0) >= PAGE_IMG_MIN * pw * ph:
                        rows.append({"cy": (y0 + y1) / 2, "h": 1.0, "items": [(x0, x1, marker)], "fixed": True, "img": True})
                if len(page.get_drawings()) >= PAGE_DRAWINGS_MIN and not tables and not any(r.get("img") for r in rows):
                    rows.append({"cy": ph, "h": 1.0, "items": [(0, 1, marker)], "fixed": True, "img": True})
            except Exception:
                pass
        rows.sort(key=lambda r: r["cy"])
        out = []
        for r in rows:
            its = sorted(r["items"])
            parts = [its[0][2]]
            for prev, cur in zip(its, its[1:]):
                parts.append((" │ " if cur[0] - prev[1] > 1.5 * r["h"] else " ") + cur[2])
            line = "".join(parts)
            if with_images and not r["fixed"] and any(is_math(t) for _, _, t in its):
                line += " " + note_math  # สูตรอ่านยากเมื่อเป็นข้อความ ให้ผู้ใช้เทียบกับสไลด์จริง
            out.append(line)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()

    return build(True), build(False)


def pdf_has_bad_pages(data: bytes) -> bool:
    """มีหน้าไหนที่ข้อความถอดตรงๆ ใช้ไม่ได้ (ว่างแต่มีรูป = หน้าสแกน, หรือมีตัวอักษรเพี้ยนมาก) ไหม"""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        with fitz.open(stream=data, filetype="pdf") as pdf:
            for i, pg in enumerate(pdf):
                plain, bad = clean_text(page_layout_text(pg, i + 1)[1])
                plain = plain.strip()
                if page_ok(plain, bad):
                    continue
                if len(plain) >= 20 or pg.get_image_info():
                    return True
    except Exception:
        pass
    return False


def extract_text(f) -> str:
    name = f.name.lower()
    data = f.getvalue()
    if name.endswith(".pdf"):
        try:  # PyMuPDF ถอดภาษาไทยได้ดีกว่า pypdf
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz

            with fitz.open(stream=data, filetype="pdf") as pdf:
                return "\n\n".join(f"--- หน้า {i + 1} ---\n" + page_layout_text(p, i + 1)[0] for i, p in enumerate(pdf))
        except ImportError:
            pass
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".docx"):
        from docx import Document

        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    if name.endswith(".pptx"):
        from pptx import Presentation

        prs = Presentation(io.BytesIO(data))
        lines = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    lines.append(shape.text_frame.text)
        return "\n".join(lines)
    return data.decode("utf-8", errors="ignore")


AI_READ_PROMPT = (
    "Transcribe only the text that is actually visible in this image, exactly as written. Keep the original language. "
    "For Thai, copy every character, vowel and tone mark exactly; never guess or rewrite a word you cannot read. "
    "Keep line breaks. Use markdown only for tables and bullet lists, never for headings. "
    "Do NOT describe pictures, photos, charts or illustrations, and do not add titles, comments or translations. "
    "If there is no readable text, return nothing."
)


def similarity(a: str, b: str) -> float:
    """ความคล้ายของข้อความสองชุด (0-1) ไม่นับช่องว่างและเครื่องหมาย markdown"""
    import difflib

    norm = lambda x: re.sub(r"[\s#\[\]*_`|\-]+", "", x)[:3000]
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


MAX_AI_PAGES = 20   # โมเดลในเครื่องอ่านทีละหน้า ช้ากว่าบนคลาวด์ จึงจำกัดจำนวนหน้า
MAX_PAGE_TOKENS = 1200   # เพดานความยาวต่อหน้า กันโมเดลวนเขียนไม่รู้จบ

# ข้อความไทยไม่มีเว้นวรรค จึงจับ "ท่อนที่วนซ้ำติดกัน" ด้วย backreference


def collapse_repeats(txt: str, min_unit: int = 4, min_rep: int = 3, lines: bool = True):
    """ตัดข้อความที่วนซ้ำ เหลือไว้ 1 รอบ คืน (ข้อความ, เคยตัดหรือไม่)
    ผลลัพธ์จาก AI: ใช้ค่าปกติ (ท่อน >= 4 ตัวอักษร ซ้ำ >= 3 รอบ) และตัดบรรทัดซ้ำติดกันด้วย
    ข้อความจากไฟล์จริง: ให้ใช้ min_unit=12, min_rep=4, lines=False จะได้ไม่ไปตัดตัวเลขในตาราง/เมทริกซ์"""
    before = len(txt)
    rx = re.compile(r"(.{%d,300}?)\1{%d,}" % (min_unit, min_rep - 1), re.S)
    for _ in range(3):
        new_txt = rx.sub(r"\1", txt)
        if new_txt == txt:
            break
        txt = new_txt
    if lines:
        out, last = [], None
        for ln in txt.split("\n"):
            key = ln.strip()
            if key and key == last:
                continue
            out.append(ln)
            if key:
                last = key
        txt = "\n".join(out)
    return txt, len(txt) < before * 0.9


def read_page(png: bytes):
    """อ่านหน้าเดียว: จำกัดความยาว + ลงโทษการซ้ำ ถ้าเจอวนลูปให้ลองใหม่ด้วยค่าที่เข้มขึ้นหนึ่งรอบ
    คืน (ข้อความ, ok) — ok=False แปลว่ายังวนอยู่แม้ลองใหม่แล้ว"""
    attempts = [
        {"temperature": 0.1, "repeat_penalty": 1.15, "num_predict": MAX_PAGE_TOKENS},
        {"temperature": 0.5, "repeat_penalty": 1.3, "top_k": 40, "num_predict": MAX_PAGE_TOKENS // 2},
    ]
    txt = ""
    for opts in attempts:
        raw = gen_content(AI_READ_PROMPT, images=[png], **opts)
        txt, looped = collapse_repeats(raw)
        if not looped:
            return txt, True
    return txt, False


def page_ok(txt: str, bad: int) -> bool:
    """หน้านี้ข้อความที่ถอดตรงๆ ใช้ได้ไหม (ไม่ว่าง ไม่มีตัวอักษรเพี้ยนมาก)"""
    return len(txt) >= 20 and bad <= max(2, len(txt) * 0.005)


def ai_read(data: bytes, mime: str, is_pdf: bool, force: bool = True):
    """ให้โมเดลที่มองเห็นภาพ (เช่น gemma3) อ่านรูป/หน้า PDF
    force=False (โหมดอัตโนมัติ): ใช้ AI เฉพาะหน้าที่ข้อความถอดตรงๆ ว่าง/เพี้ยน หน้าอื่นใช้ข้อความจริงในไฟล์
    ถ้า AI อ่านหน้าไหนแล้ววนซ้ำไม่เลิก จะถอยกลับไปใช้ข้อความถอดตรงๆ ของหน้านั้น
    คืน (ข้อความ, จำนวนครั้งที่เรียก AI, จำนวนหน้าที่อ่านถ้าไฟล์ถูกตัด หรือ None)"""
    if len(data) > 18 * 1024 * 1024:
        raise ValueError(t("upload_toolarge"))
    if not is_pdf:
        return read_page(data)[0], 1, None
    import fitz  # pymupdf

    doc = fitz.open(stream=data, filetype="pdf")
    n = len(doc)
    out, seen, calls = [], set(), 0
    for i in range(n):
        with_img, plain = page_layout_text(doc[i], i + 1)
        plain, bad = clean_text(plain)
        plain, _ = collapse_repeats(plain.strip(), 12, 4, False)
        native, _ = clean_text(with_img)
        native, _ = collapse_repeats(native.strip(), 12, 4, False)
        native = f"--- หน้า {i + 1} ---\n" + native if native else native
        if not force and page_ok(plain, bad):
            out.append(native)
            continue
        if calls >= MAX_AI_PAGES:  # เกินโควตา AI แล้ว ใช้ข้อความถอดตรงๆ ของหน้านั้นแทน
            if plain:
                out.append(native)
            continue
        png = doc[i].get_pixmap(dpi=130).tobytes("png")
        page, ok = read_page(png)
        calls += 1
        page = page.strip()
        if (not ok or len(page) < 10) and plain:
            page = native
        elif page_ok(plain, bad) and similarity(plain, page) < 0.85:
            page = native  # AI อ่านต่างจากข้อความจริงในไฟล์มาก (โมเดลเล็กอ่านไทยเพี้ยน) เชื่อข้อความในไฟล์ดีกว่า
        if page is not native and page:
            body = page
            if body in seen:  # หน้าที่ AI อ่านได้เหมือนหน้าก่อนเป๊ะ (โมเดลวนซ้ำข้ามหน้า) ไม่เอามาต่อ
                continue
            seen.add(body)
            page = f"--- หน้า {i + 1} ---\n" + body
        if page:
            out.append(page)
    return "\n\n".join(out), calls, (MAX_AI_PAGES if calls >= MAX_AI_PAGES and n > MAX_AI_PAGES else None)


def to_markdown(d: dict) -> str:
    out = ["# Study Set", "", "## Summary", "", d["summary"], "", "## Flashcards", ""]
    for i, c in enumerate(d["flashcards"], 1):
        out += [f"{i}. **{c['q']}**", f"   - {c['a']}"]
    out += ["", "## Quiz", ""]
    for i, q in enumerate(d["quiz"], 1):
        out.append(f"{i}. {q['q']}")
        for j, ch in enumerate(q["choices"]):
            out.append(f"   - {'ABCDEFGH'[j]}. {ch}")
        out.append(f"   - Answer: {'ABCDEFGH'[q['answer']]}. {q['choices'][q['answer']]}")
        if q.get("why"):
            out.append(f"   - Why: {q['why']}")
        out.append("")
    return "\n".join(out)


# =====================================================================
# สถานะ + callbacks
# =====================================================================
S = st.session_state
S.setdefault("notes", "")
S.setdefault("gen_id", 0)
S.setdefault("fc_i", 0)
S.setdefault("fc_res", {})  # ผลตรวจคำตอบแฟลชการ์ด key = "gen_id:ลำดับการ์ด"
S.setdefault("fc_show", False)
S.setdefault("quiz_round", 0)
S.setdefault("quiz_submitted", False)
S.setdefault("quiz_answers", [])
S.setdefault("qa_history", [])
S.setdefault("qa_cache", {})
S.setdefault("sets_cache", {})


def load_sample(name: str):
    S.notes = SAMPLES[name][S.get("lang", "th")]


def fc_move(delta: int, n: int):
    S.fc_i = (S.fc_i + delta) % max(n, 1)
    S.fc_show = False


def fc_flip():
    S.fc_show = not S.fc_show


def quiz_retry():
    S.quiz_submitted = False
    S.quiz_answers = []
    S.quiz_round += 1


def clear_history():
    S.qa_history = []


def set_new_data(data: dict):
    S.data = data
    S.gen_id += 1
    S.fc_i = 0
    S.fc_show = False
    S.fc_res = {}
    S.quiz_round = 0
    S.quiz_submitted = False
    S.quiz_answers = []
    S.qa_history = []


# =====================================================================
# หน้าเว็บ
# =====================================================================
with st.expander(t("notice_title")):
    st.markdown("\n".join(f"- {t(k)}" for k in ("notice_privacy", "notice_ai", "notice_quota", "notice_pdf", "notice_sidebar")))

# ----- ตัวดูสไลด์ต้นฉบับ (เทียบกับข้อความที่ถอดได้) -----
def _open_pdf(data: bytes):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz.open(stream=data, filetype="pdf")


@st.cache_data(show_spinner=False)
def pdf_page_count(name: str, size: int, _data: bytes) -> int:
    with _open_pdf(_data) as doc:
        return len(doc)


@st.cache_data(show_spinner=False, max_entries=60)
def render_slide(name: str, size: int, i: int, _data: bytes) -> bytes:
    with _open_pdf(_data) as doc:
        return doc[i].get_pixmap(dpi=110).tobytes("png")


# ----- อัปโหลดไฟล์ -----
files = st.file_uploader(
    t("upload_label"),
    type=["pdf", "docx", "pptx", "txt", "md", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="uploader",
)
sig = (tuple((f.name, f.size) for f in files), READ_MODE)
if sig != S.get("file_sig", ((), "auto")):
    S.file_sig = sig
    S.pdf_files = {}  # เก็บ PDF ไว้ให้ตัวดูสไลด์
    msgs, parts = [], []
    for f in files:
        lname, data = f.name.lower(), f.getvalue()
        is_pdf = lname.endswith(".pdf")
        is_img = lname.endswith((".png", ".jpg", ".jpeg"))
        if is_pdf:
            S.pdf_files[f.name] = data
        txt, bad, use_ai = "", 0, False
        try:
            if is_img:
                if READ_MODE == "fast":
                    msgs.append(("upload_img_fast", "warning", {"name": f.name}))
                    continue
                use_ai = True
            else:
                txt, bad = clean_text(extract_text(f))
                txt = txt.strip()
                txt, deduped = collapse_repeats(txt, 12, 4, False)  # ไฟล์ที่ข้อความซ้ำผิดปกติ (เช่น PDF/สไลด์ที่ถอดซ้ำ)
                if deduped:
                    msgs.append(("upload_deduped", "info", {"name": f.name}))
                broken = len(txt) < 20 or bad > max(3, len(txt) * 0.005)
                use_ai = is_pdf and (READ_MODE == "ai" or (READ_MODE == "auto" and (broken or pdf_has_bad_pages(data))))
        except Exception as e:
            msgs.append(("upload_fail", "error", {"name": f.name, "err": str(e)}))
            if not is_pdf:
                continue
            use_ai = READ_MODE != "fast"
        if use_ai:
            try:
                mime = "application/pdf" if is_pdf else ("image/png" if lname.endswith(".png") else "image/jpeg")
                with st.spinner(f"AI: {f.name}"):
                    ai_txt, calls, cut_at = ai_read(data, mime, is_pdf, force=(READ_MODE == "ai" or not is_pdf))
                ai_txt, _ = clean_text(ai_txt)
                ai_txt, _ = collapse_repeats(ai_txt, 12, 4, False)
                if len(ai_txt.strip()) >= 20:
                    txt, bad = ai_txt.strip(), (0 if calls else bad)
                    if calls:
                        msgs.append(("upload_ai_used", "success", {"name": f.name, "n": calls}))
                    if cut_at:
                        msgs.append(("upload_ai_cut", "warning", {"name": f.name, "n": cut_at}))
            except Exception as e:
                msgs.append(("upload_ai_fail", "warning", {"name": f.name, "err": t(classify_error(e))}))
        if len(txt) < 20:
            msgs.append(("upload_empty", "warning", {"name": f.name}))
        else:
            parts.append(f"=== {f.name} ===\n{txt}")
            if bad:
                msgs.append(("upload_garbled", "warning", {"name": f.name, "n": bad}))
    if parts:
        S.notes = "\n\n".join(parts)
        msgs.insert(0, ("upload_ok", "success", {"n": len(S.notes), "f": len(parts)}))
    S.upload_msgs = msgs
for key, level, args in S.get("upload_msgs", []):
    getattr(st, level)(t(key, **args))

# ----- ช่องโน้ต -----
st.text_area(t("notes_label"), height=240, placeholder=t("notes_ph"), key="notes")

_pdfs = S.get("pdf_files") or {}
if _pdfs:
    with st.expander(t("slide_view")):
        try:
            _name = st.selectbox(t("slide_file"), list(_pdfs), key="slide_file") if len(_pdfs) > 1 else next(iter(_pdfs))
            _data = _pdfs[_name]
            _n = pdf_page_count(_name, len(_data), _data)
            _pg = st.number_input(t("slide_page"), min_value=1, max_value=_n, value=1, step=1, key="slide_pg")
            st.image(render_slide(_name, len(_data), int(_pg) - 1, _data), width="stretch")
        except Exception as e:
            st.caption(f"{t('slide_fail')} ({e})")
notes = S.notes

def slide_ref(item: dict, inline: bool = False, expanded: bool = False):
    """บอกว่าข้อ/การ์ดนี้ควรไปศึกษาที่สไลด์หน้าไหน: inline=True และหน้านั้นมีรูป/ตาราง/สูตร = แสดงรูปเลย
    นอกนั้นแสดงเลขหน้า + กล่องกดดูสไลด์"""
    pg, name = item.get("page", 0), item.get("file", "")
    if not pg:
        return
    where = t("qz_study", p=pg) + (f" · {item['title']}" if item.get("title") else "")
    data = (S.get("pdf_files") or {}).get(name)
    st.caption(where)
    if not data:
        return
    try:
        if inline and item.get("visual"):
            st.image(render_slide(name, len(data), pg - 1, data), width="stretch")
        else:
            with st.expander(t("fc_view_slide", p=pg), expanded=expanded):
                st.image(render_slide(name, len(data), pg - 1, data), width="stretch")
    except Exception as e:
        st.caption(f"{t('slide_fail')} ({e})")


def quiet_button(col, label, **kw):
    """ปุ่มข้อความเรียบๆ (ถ้า Streamlit รุ่นเก่าไม่รองรับ จะใช้ปุ่มปกติแทน)"""
    try:
        return col.button(label, type="tertiary", **kw)
    except Exception:
        return col.button(label, **kw)


sc = st.columns([1.6, 1, 1, 1, 2], vertical_alignment="center")
sc[0].caption(t("chars", n=len(notes)) + "  ·  " + t("samples"))
for col, name in zip(sc[1:4], SAMPLES):
    quiet_button(col, name, key=f"sample_{name}", on_click=load_sample, args=(name,))

if len(notes) > MAX_CHARS:
    st.warning(t("truncated", n=len(notes), m=MAX_CHARS))

has_data = bool(S.get("data"))
b1, b2, _ = st.columns([1.3, 1, 3])
gen_clicked = b1.button(t("btn_generate"), type="primary", key="btn_generate")
regen_clicked = b2.button(t("btn_regen"), key="btn_regen")
st.caption(t("notice_line"))

if gen_clicked or regen_clicked:
    if len(notes.strip()) < 50:
        st.warning(t("too_short"))
    else:
        sig_in = json.dumps([notes, N_CARDS, N_QUIZ, DIFF, OUT_LANG, GEN_MODEL, NUM_CTX])
        set_key = hashlib.md5(sig_in.encode()).hexdigest()
        data = None
        if set_key in S.sets_cache and not regen_clicked:
            data = S.sets_cache[set_key]
            st.toast(t("reused"))
        else:
            try:
                with st.spinner(t("spin_gen")):
                    data = generate_study_set(notes, N_CARDS, N_QUIZ, DIFF, OUT_LANG, set_key)
                S.sets_cache[set_key] = data
                st.toast(t("done"))
            except Exception as e:
                show_error(e)
        if data:
            set_new_data(data)
            rag_key = hashlib.md5(notes.encode()).hexdigest()
            if S.get("rag", {}).get("hash") != rag_key:
                S.rag = None
                try:
                    with st.spinner(t("spin_embed")):
                        S.rag = build_rag(notes, rag_key)
                except Exception as e:
                    st.warning(t("rag_unavailable", msg=t(classify_error(e))))
            if S.get("rag") and S.rag.get("truncated"):
                st.info(t("rag_trunc", n=MAX_CHUNKS))

# ----- ผลลัพธ์ -----
d = S.get("data")
if not d:
    st.markdown(f"**{t('empty_title')}**")
    st.caption(t("empty_body"))
else:
    rag = S.get("rag")
    pills = [t("stat_cards", n=len(d["flashcards"])), t("stat_quiz", n=len(d["quiz"]))]
    if rag:
        pills.append(t("stat_chunks", n=len(rag["chunks"])))
    st.caption("  ·  ".join(pills))

    t1, t2, t3, t4 = st.tabs([t("tab_sum"), t("tab_cards"), t("tab_quiz"), t("tab_qa")])

    # ----- สรุป -----
    with t1:
        if d.get("tone_warn"):
            st.warning(t("tone_warn"))
        st.markdown(d["summary"])
        st.download_button(t("download"), to_markdown(d), file_name="study-set.md", mime="text/markdown", key="btn_dl")
        st.caption(t("notice_short"))

    # ----- แฟลชการ์ด -----
    with t2:
        cards = d["flashcards"]
        if not cards:
            st.info(t("no_cards"))
        else:
            n = len(cards)
            i = S.fc_i % n
            show = S.fc_show
            card = cards[i]
            gid = S.gen_id
            rk = f"{gid}:{i}"
            res = S.fc_res.get(rk)
            st.progress((i + 1) / n, text=t("card_of", i=i + 1, n=n))

            # รูป/อ้างอิงสไลด์: การ์ดที่หน้าสไลด์มีรูป/ตาราง/สูตรแสดงรูปเลย ที่เหลือแสดงเลขหน้าและให้กดดูสไลด์ได้
            pg, src_name = card.get("page", 0), card.get("file", "")
            pdf_bytes = (S.get("pdf_files") or {}).get(src_name)
            if pg and pdf_bytes:
                if card.get("visual"):
                    try:
                        st.image(render_slide(src_name, len(pdf_bytes), pg - 1, pdf_bytes), caption=t("fc_img_cap", p=pg), width="stretch")
                    except Exception:
                        st.caption(t("fc_ref", p=pg))
                else:
                    st.caption(t("fc_ref", p=pg))
                    with st.expander(t("fc_view_slide", p=pg)):
                        try:
                            st.image(render_slide(src_name, len(pdf_bytes), pg - 1, pdf_bytes), width="stretch")
                        except Exception as e:
                            st.caption(f"{t('slide_fail')} ({e})")
            elif pg:
                st.caption(t("fc_ref", p=pg))

            label = t("lbl_a") if show else t("lbl_q")
            body = card["a" if show else "q"]
            st.markdown(
                f'<div class="fcard {"a" if show else "q"}"><div><small>{esc(label)}</small>{esc(body)}</div></div>',
                unsafe_allow_html=True,
            )

            # ช่องคำตอบ: ต้องตรวจ (หรือกดข้าม) ก่อนจึงพลิกการ์ดได้
            user_ans = st.text_area(t("fc_ans_label"), key=f"fc_ans_{gid}_{i}", height=100)
            c1, c2 = st.columns(2)
            do_check = c1.button(t("fc_check"), key=f"fc_check_{gid}_{i}", type="primary")
            do_skip = quiet_button(c2, t("fc_skip"), key=f"fc_skip_{gid}_{i}")
            if do_check:
                if not (user_ans or "").strip():
                    st.warning(t("fc_type_first"))
                else:
                    try:
                        with st.spinner(t("fc_checking")):
                            S.fc_res[rk] = judge_answer(card["q"], card["a"], user_ans, card.get("ev", ""))
                        res = S.fc_res[rk]
                    except Exception as e:
                        show_error(e)
            elif do_skip:
                S.fc_res[rk] = {"verdict": "skipped", "feedback": ""}
                res = S.fc_res[rk]
            if res:
                fb = res.get("feedback", "")
                if res["verdict"] == "correct":
                    st.success(f"{t('fc_ok')} {fb}")
                elif res["verdict"] == "partial":
                    st.warning(f"{t('fc_partial')} {fb}")
                elif res["verdict"] == "incorrect":
                    st.error(f"{t('fc_bad')} {fb}")
                elif res["verdict"] == "unknown":
                    st.info(t("fc_unknown"))

            f1, f2, f3 = st.columns(3)
            f1.button(t("prev"), key="fc_prev", on_click=fc_move, args=(-1, n))
            f2.button(t("flip"), key="fc_flip", on_click=fc_flip, type="primary", disabled=res is None, help=t("fc_flip_help"))
            f3.button(t("next"), key="fc_next", on_click=fc_move, args=(1, n))

    # ----- ข้อสอบ -----
    with t3:
        quiz = d["quiz"]
        gid, rnd = S.gen_id, S.quiz_round
        if not quiz:
            st.info(t("no_quiz"))
        elif not S.quiz_submitted:
            with st.form(f"quiz_form_{gid}_{rnd}"):
                for i, q in enumerate(quiz):
                    slide_ref(q, inline=bool(q.get("figure")))
                    st.radio(f"**{t('quiz_q', i=i + 1)}.** {q['q']}", q["choices"], index=None, key=f"q{i}_{gid}_{rnd}")
                submitted = st.form_submit_button(t("btn_check"), type="primary")
            if submitted:
                S.quiz_answers = [S.get(f"q{i}_{gid}_{rnd}") for i in range(len(quiz))]
                S.quiz_submitted = True
                st.rerun()
        else:
            answers = S.quiz_answers
            score = sum(1 for q, a in zip(quiz, answers) if a == q["choices"][q["answer"]])
            blank = sum(1 for a in answers if a is None)
            pct = score / len(quiz)
            msg = t("score_hi") if pct >= 0.8 else t("score_mid") if pct >= 0.5 else t("score_low")
            st.markdown(f'{esc(t("score"))}<br><span class="score">{score} / {len(quiz)}</span>', unsafe_allow_html=True)
            st.progress(pct, text=msg)
            if blank:
                st.warning(t("unanswered", n=blank))
            for i, (q, a) in enumerate(zip(quiz, answers)):
                right = q["choices"][q["answer"]]
                ok = a == right
                verdict = t("correct") if ok else t("wrong", ans=right)
                why = f'<div class="why">{esc(q["why"])}</div>' if q.get("why") else ""
                st.markdown(
                    f'<div class="res {"ok" if ok else "bad"}"><div class="q">{esc(t("quiz_q", i=i + 1))}. {esc(q["q"])}</div>'
                    f"<div>{esc(verdict)}</div>{why}</div>",
                    unsafe_allow_html=True,
                )
                slide_ref(q, inline=False, expanded=not ok)  # ข้อที่ผิดเปิดสไลด์ให้เลย
            st.button(t("btn_retry"), key="btn_retry", on_click=quiz_retry, type="primary")

    # ----- ถามตอบ -----
    with t4:
        if not rag:
            st.warning(t("rag_off"))
        mode = st.radio(
            t("mode_label"), ["notes", "general"], index=1, horizontal=True,
            format_func=lambda c: t("mode_" + c), key="qa_mode",
        )
        if mode == "notes" and not rag:
            pass
        else:
            st.caption(t("hint_" + mode))
            with st.form("ask_form", clear_on_submit=True):
                question = st.text_input(t("ask_label"), placeholder=t("ask_ph"), key="ask_input")
                asked = st.form_submit_button(t("ask_btn"), type="primary")
            if asked and question.strip():
                ck = (rag["hash"] if rag else "", mode, question.strip().lower())
                if ck in S.qa_cache:
                    S.qa_history.append(dict(S.qa_cache[ck], q=question, cached=True))
                else:
                    try:
                        with st.spinner("..."):
                            item = ask_rag(question, rag, mode, S.qa_history)
                        S.qa_cache[ck] = item
                        S.qa_history.append(dict(item, q=question, cached=False))
                    except Exception as e:
                        show_error(e)
            for idx, item in reversed(list(enumerate(S.qa_history))):
                with st.chat_message("user"):
                    st.write(item["q"])
                with st.chat_message("assistant"):
                    with st.container(key=f"ans_notes_{idx}"):
                        st.markdown(f'<span class="tag n">{esc(t("sec_notes"))}</span>', unsafe_allow_html=True)
                        st.markdown(item["from_notes"] or t("not_found"))
                        st.caption(t("sec_notes_cap"))
                    if item["beyond"]:
                        with st.container(key=f"ans_beyond_{idx}"):
                            st.markdown(f'<span class="tag b">{esc(t("sec_beyond"))}</span>', unsafe_allow_html=True)
                            st.markdown(item["beyond"])
                            st.caption(t("sec_beyond_cap_web") if item["mode"] == "web" else t("sec_beyond_cap"))
                            if item["links"]:
                                st.markdown(f"**{t('web_sources')}**\n" + "\n".join(f"- [{n}]({u})" for n, u in item["links"]))
                    if item["cached"]:
                        st.caption(t("cached"))
                    if item["srcs"]:
                        with st.expander(t("sources")):
                            for s_ in item["srcs"]:
                                st.markdown("> " + s_.replace("\n", "\n> "))
            if S.qa_history:
                st.button(t("ask_clear"), key="btn_clear", on_click=clear_history)

st.divider()
st.caption(t("footer"))
st.caption(f"Ollama · {GEN_MODEL} · {EMBED_MODEL}")
