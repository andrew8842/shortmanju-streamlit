"""
短漫剧生成器 - Streamlit版 (Seko式左右布局)
左边对话栏 + 右边实时预览
"""

import streamlit as st
import json
import time
import uuid
import os
from datetime import datetime
import hashlib
import hmac
import base64
from PIL import Image
import io

# 页面配置
st.set_page_config(
    page_title="短漫剧生成器 · 对话式",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== 自定义CSS（仿Seko风格）====================
st.markdown("""
<style>
    /* 整体布局 */
    .main > div {
        padding: 0;
    }
    
    /* 左右分栏 */
    .chat-container {
        background: #1a1a1a;
        height: 100vh;
        overflow-y: auto;
        padding: 20px;
        border-right: 1px solid #333;
    }
    
    .preview-container {
        background: #0a0a0a;
        height: 100vh;
        overflow-y: auto;
        padding: 20px;
    }
    
    /* 对话气泡 */
    .user-message {
        background: #2b5278;
        color: white;
        padding: 15px;
        border-radius: 20px 20px 5px 20px;
        margin: 10px 0;
        max-width: 80%;
        float: right;
        clear: both;
    }
    
    .assistant-message {
        background: #2a2a2a;
        color: #e0e0e0;
        padding: 15px;
        border-radius: 20px 20px 20px 5px;
        margin: 10px 0;
        max-width: 80%;
        float: left;
        clear: both;
        border: 1px solid #404040;
    }
    
    .system-message {
        background: #333333;
        color: #ffd700;
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
        text-align: center;
        font-size: 14px;
        clear: both;
    }
    
    /* 预览卡片 */
    .preview-card {
        background: #1e1e1e;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid #333;
    }
    
    .preview-title {
        color: #8a2be2;
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 15px;
        border-bottom: 1px solid #333;
        padding-bottom: 10px;
    }
    
    .story-element {
        background: #252525;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #1657ff;
    }
    
    .shot-card {
        background: #252525;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        display: flex;
        align-items: center;
    }
    
    .shot-number {
        background: #1657ff;
        color: white;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 15px;
        font-weight: bold;
    }
    
    /* 输入框 */
    .chat-input {
        position: fixed;
        bottom: 20px;
        left: 20px;
        right: 50%;
        background: #2a2a2a;
        border: 1px solid #404040;
        border-radius: 30px;
        padding: 10px 20px;
        color: white;
    }
    
    /* 确认按钮 */
    .confirm-button {
        background: linear-gradient(135deg, #1657ff, #8a2be2);
        color: white;
        border: none;
        padding: 10px 25px;
        border-radius: 30px;
        cursor: pointer;
        font-weight: bold;
        margin: 10px 0;
    }
    
    /* 资产标签 */
    .asset-tag {
        background: #2a2a2a;
        border: 1px solid #404040;
        padding: 5px 12px;
        border-radius: 20px;
        display: inline-block;
        margin: 3px;
        font-size: 12px;
        color: #aaa;
    }
    
    .asset-tag.character {
        border-color: #ff6b6b;
        color: #ff6b6b;
    }
    
    .asset-tag.scene {
        border-color: #4ecdc4;
        color: #4ecdc4;
    }
    
    .asset-tag.prop {
        border-color: #ffe66d;
        color: #ffe66d;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初始化会话状态 ====================
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'api_configured' not in st.session_state:
    st.session_state.api_configured = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "🎬 欢迎使用短漫剧生成器！我是您的AI助手，将引导您一步步完成创作。"},
        {"role": "assistant", "content": "首先，请先在右侧配置您的火山引擎API密钥。"}
    ]
if 'asset_library' not in st.session_state:
    st.session_state.asset_library = {
        'characters': {},
        'scenes': {},
        'props': {}
    }
if 'current_data' not in st.session_state:
    st.session_state.current_data = {
        '剧本': None,
        '想法': '',
        '风格参数': {},
        '故事元素': {},
        '分镜': [],
        '关键词': {},
        '分镜关键词': [],
        '视频结果': None
    }
if 'preview_content' not in st.session_state:
    st.session_state.preview_content = {
        'type': 'welcome',
        'data': None
    }

# ==================== 创建左右分栏 ====================
left_col, right_col = st.columns([1, 1.2])

# ==================== 左侧：对话栏 ====================
with left_col:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # 显示对话历史
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-message">{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            st.markdown(f'<div class="assistant-message">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="system-message">{msg["content"]}</div>', unsafe_allow_html=True)
    
    # 根据步骤显示不同的对话选项
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
    
    # ==================== 步骤1：API配置 ====================
    if not st.session_state.api_configured:
        with st.container():
            st.markdown('<div class="assistant-message">请配置您的火山引擎API密钥：</div>', unsafe_allow_html=True)
            ak = st.text_input("Access Key ID", type="password", key="ak_input")
            sk = st.text_input("Secret Access Key", type="password", key="sk_input")
            region = st.selectbox("区域", ["cn-beijing", "cn-shanghai", "ap-southeast-1"])
            
            if st.button("🔑 验证并保存", use_container_width=True):
                if ak and sk:
                    st.session_state.api_configured = True
                    st.session_state.ak = ak
                    st.session_state.sk = sk
                    st.session_state.region = region
                    st.session_state.chat_history.append({"role": "system", "content": "✅ API配置成功！"})
                    st.session_state.chat_history.append({"role": "assistant", "content": "现在开始步骤1：请上传剧本或描述您的想法。"})
                    st.rerun()
    
    # ==================== 步骤1：输入创意 ====================
    elif st.session_state.step == 1:
        with st.container():
            option = st.radio("选择输入方式：", ["📄 上传剧本", "💡 直接描述"])
            
            if option == "📄 上传剧本":
                uploaded_file = st.file_uploader("选择文件", type=['txt', 'pdf', 'doc', 'docx'])
                if uploaded_file and st.button("✅ 确认上传"):
                    st.session_state.current_data['剧本'] = uploaded_file.name
                    st.session_state.chat_history.append({"role": "user", "content": f"上传了剧本：{uploaded_file.name}"})
                    st.session_state.chat_history.append({"role": "assistant", "content": "剧本已收到！现在进行步骤2：请设置影像风格。"})
                    st.session_state.step = 2
                    st.rerun()
            else:
                idea = st.text_area("描述您的想法", placeholder="例如：一个关于未来东京的少女与AI机器人的温情短剧")
                if idea and st.button("✅ 确认描述"):
                    st.session_state.current_data['想法'] = idea
                    st.session_state.chat_history.append({"role": "user", "content": f"我的想法：{idea[:50]}..."})
                    st.session_state.chat_history.append({"role": "assistant", "content": "想法已记录！现在进行步骤2：请设置影像风格。"})
                    st.session_state.step = 2
                    st.rerun()
    
    # ==================== 步骤2：设置风格 ====================
    elif st.session_state.step == 2:
        with st.container():
            st.markdown('<div class="assistant-message">请设置影像风格：</div>', unsafe_allow_html=True)
            
            style = st.text_input("🎨 影像风格", "新海诚风")
            reference = st.text_input("📽️ 参考影片", "你的名字。")
            core = st.text_input("📢 核心诉求", "治愈、青春")
            ratio = st.selectbox("📐 输出比例", ["16:9", "9:16", "4:3", "1:1"])
            duration = st.slider("⏱️ 时长(秒)", 5, 300, 60)
            
            if st.button("✅ 确认风格设置"):
                st.session_state.current_data['风格参数'] = {
                    '风格': style,
                    '参考影片': reference,
                    '核心诉求': core,
                    '比例': ratio,
                    '时长': duration
                }
                st.session_state.chat_history.append({"role": "user", "content": f"风格：{style}，参考：{reference}，时长：{duration}秒"})
                st.session_state.chat_history.append({"role": "assistant", "content": "风格已设置！现在进行步骤3：生成故事元素。"})
                st.session_state.step = 3
                st.rerun()
    
    # ==================== 步骤3：生成故事 ====================
    elif st.session_state.step == 3:
        with st.container():
            if not st.session_state.current_data.get('故事元素'):
                if st.button("✨ 生成故事元素"):
                    with st.spinner("AI正在构思..."):
                        time.sleep(2)
                        
                        idea = st.session_state.current_data.get('想法', '')
                        if '机器人' in idea or '未来' in idea:
                            story = {
                                'name': '「未来记忆」',
                                'oneLiner': '一个仿生人寻找失落的童年记忆',
                                'synopsis': '2147年，仿生人工程师小林发现自己的记忆芯片中存在无法识别的数据片段...',
                                'bio': '小林 (23岁仿生人)，琥珀色电子眼，银发；阿杰 (人类黑客)'
                            }
                        else:
                            story = {
                                'name': '「记忆中的回响」',
                                'oneLiner': '一个少女与仿生人在废墟都市寻找最后一首情歌',
                                'synopsis': '近未来，东京废墟，少女Mila与守护型仿生人Kenji一同寻找能唤醒亡母记忆的歌曲。',
                                'bio': 'Mila, 16岁, 琥珀色眼睛, 短发, 机械右臂; Kenji, 高大仿生人, 左肩有红色涂装'
                            }
                        
                        st.session_state.current_data['故事元素'] = story
                        
                        # 更新预览
                        st.session_state.preview_content = {
                            'type': 'story',
                            'data': story
                        }
                        
                        st.session_state.chat_history.append({"role": "assistant", "content": f"✨ 故事生成成功！名称：{story['name']}"})
                        st.rerun()
            
            # 确认故事
            if st.session_state.current_data.get('故事元素'):
                story = st.session_state.current_data['故事元素']
                st.markdown(f'<div class="assistant-message">故事名称：{story["name"]}\n\n满意吗？</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 满意，继续"):
                        st.session_state.chat_history.append({"role": "user", "content": "满意，继续"})
                        st.session_state.chat_history.append({"role": "assistant", "content": "现在生成分镜..."})
                        time.sleep(1)
                        
                        # 生成分镜
                        shots = [
                            {'id': 1, 'type': '全景', 'description': '东京塔废墟，Mila和Kenji站在高架桥上，夕阳染红天空'},
                            {'id': 2, 'type': '中景', 'description': 'Mila低头看着机械臂，Kenji伸手触碰她的肩膀'},
                            {'id': 3, 'type': '特写', 'description': '旧式播放器在Mila手中亮起，浮现全息界面'},
                            {'id': 4, 'type': '远景', 'description': '两人走入废弃音乐厅，舞台中央有一架钢琴'}
                        ]
                        
                        st.session_state.current_data['分镜'] = shots
                        st.session_state.preview_content = {
                            'type': 'shots',
                            'data': shots
                        }
                        
                        st.session_state.chat_history.append({"role": "assistant", "content": "分镜已生成，请查看右侧预览。"})
                        st.rerun()
                
                with col2:
                    mod = st.text_input("✏️ 修改意见")
                    if mod and st.button("重新生成"):
                        st.session_state.chat_history.append({"role": "user", "content": f"修改：{mod}"})
                        st.session_state.chat_history.append({"role": "assistant", "content": "好的，根据您的意见重新生成..."})
                        # 这里可以调用API重新生成
                        st.rerun()
    
    # ==================== 后续步骤类似，按此模式继续 ====================
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== 右侧：预览栏 ====================
with right_col:
    st.markdown('<div class="preview-container">', unsafe_allow_html=True)
    
    # 顶部显示资产库
    if st.session_state.asset_library['characters'] or st.session_state.asset_library['scenes']:
        st.markdown("### 📚 资产库")
        cols = st.columns(3)
        with cols[0]:
            for char_id, char in st.session_state.asset_library['characters'].items():
                st.markdown(f'<span class="asset-tag character">👤 {char.get("name", "角色")}</span>', unsafe_allow_html=True)
        with cols[1]:
            for scene_id, scene in st.session_state.asset_library['scenes'].items():
                st.markdown(f'<span class="asset-tag scene">🏙️ {scene.get("name", "场景")}</span>', unsafe_allow_html=True)
        with cols[2]:
            for prop_id, prop in st.session_state.asset_library['props'].items():
                st.markdown(f'<span class="asset-tag prop">📦 {prop.get("name", "道具")}</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 根据预览类型显示不同内容
    preview_type = st.session_state.preview_content['type']
    preview_data = st.session_state.preview_content['data']
    
    if preview_type == 'welcome':
        st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <h1 style="color: #8a2be2;">🎬 短漫剧生成器</h1>
            <p style="color: #666;">左侧对话，右侧实时预览</p>
            <p style="color: #444; margin-top: 30px;">请先在左侧配置API密钥开始创作</p>
        </div>
        """, unsafe_allow_html=True)
    
    elif preview_type == 'story':
        story = preview_data
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        st.markdown('<div class="preview-title">📖 生成的故事</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="story-element"><b>名称：</b> {story["name"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="story-element"><b>一句话：</b> {story["oneLiner"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="story-element"><b>梗概：</b> {story["synopsis"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="story-element"><b>人物：</b> {story["bio"]}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    elif preview_type == 'shots':
        shots = preview_data
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        st.markdown('<div class="preview-title">🎬 生成的分镜</div>', unsafe_allow_html=True)
        
        for shot in shots:
            st.markdown(f'''
            <div class="shot-card">
                <div class="shot-number">{shot["id"]}</div>
                <div>
                    <b>{shot["type"]}</b><br>
                    {shot["description"]}
                </div>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    elif preview_type == 'keywords':
        keywords = preview_data
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        st.markdown('<div class="preview-title">🔑 形象关键词</div>', unsafe_allow_html=True)
        
        tabs = st.tabs(["人物", "场景", "道具"])
        with tabs[0]:
            for char in keywords.get('characters', []):
                st.markdown(f'<div class="story-element">👤 {char}</div>', unsafe_allow_html=True)
        with tabs[1]:
            for scene in keywords.get('scenes', []):
                st.markdown(f'<div class="story-element">🏙️ {scene}</div>', unsafe_allow_html=True)
        with tabs[2]:
            for prop in keywords.get('props', []):
                st.markdown(f'<div class="story-element">📦 {prop}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    elif preview_type == 'video':
        st.markdown('<div class="preview-card">', unsafe_allow_html=True)
        st.markdown('<div class="preview-title">🎥 视频预览</div>', unsafe_allow_html=True)
        
        # 模拟视频播放器
        st.video("https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4")
        
        if preview_data:
            st.markdown(f'''
            <div style="background: #252525; padding: 15px; border-radius: 10px; margin-top: 15px;">
                <b>任务ID：</b> {preview_data.get("task_id", "N/A")}<br>
                <b>时长：</b> {preview_data.get("duration", 60)}秒<br>
                <b>配音：</b> {preview_data.get("voice", "温柔女声")}<br>
                <b>BGM：</b> {preview_data.get("bgm", "治愈纯音乐")}
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 显示当前步骤提示
    st.markdown(f'''
    <div style="position: fixed; bottom: 20px; right: 30px; background: #2a2a2a; padding: 10px 20px; border-radius: 30px; border: 1px solid #404040;">
        步骤 {st.session_state.step}/6
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)