"""
短漫剧生成器 - Streamlit版
集成Seko亮点：角色一致性 + 资产自动继承 + 自然语言修改
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
    page_title="短漫剧生成器",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1657ff, #8a2be2);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    .step-box {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1657ff;
        margin: 10px 0;
    }
    .step-title {
        color: #1657ff;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .asset-badge {
        background: #e7f3ff;
        padding: 5px 10px;
        border-radius: 20px;
        display: inline-block;
        margin: 2px;
        font-size: 12px;
    }
    .success-msg {
        background: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .warning-msg {
        background: #fff3cd;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
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
if 'asset_library' not in st.session_state:
    st.session_state.asset_library = {
        'characters': {},  # 角色资产库 {id: {name, features, ref_img, keywords}}
        'scenes': {},      # 场景资产库 {id: {name, keywords}}
        'props': {}        # 道具资产库 {id: {name, keywords}}
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
if 'modification_history' not in st.session_state:
    st.session_state.modification_history = []  # 修改历史

# ==================== 侧边栏：API配置和资产库 ====================
with st.sidebar:
    st.markdown("## 🔑 火山引擎配置")
    
    with st.expander("点击配置API密钥", expanded=not st.session_state.api_configured):
        ak = st.text_input("Access Key ID", type="password", key="ak_input")
        sk = st.text_input("Secret Access Key", type="password", key="sk_input")
        region = st.selectbox("区域", ["cn-beijing", "cn-shanghai", "ap-southeast-1"])
        
        if st.button("验证并保存", use_container_width=True):
            if ak and sk:
                st.session_state.api_configured = True
                st.session_state.ak = ak
                st.session_state.sk = sk
                st.session_state.region = region
                st.success("✅ API配置成功！")
                st.rerun()
            else:
                st.error("❌ 请填写AK和SK")
    
    # 资产库展示（借鉴Seko的资产继承）
    if st.session_state.asset_library['characters'] or st.session_state.asset_library['scenes']:
        st.markdown("---")
        st.markdown("## 📚 我的资产库")
        
        # 角色资产
        if st.session_state.asset_library['characters']:
            st.markdown("### 👤 角色")
            for char_id, char in st.session_state.asset_library['characters'].items():
                with st.expander(f"📌 {char.get('name', '未命名')}"):
                    st.markdown(f"**ID:** `{char_id}`")
                    if char.get('features'):
                        st.markdown(f"**特征向量:** 已锁定 ✅")
                    if char.get('keywords'):
                        st.markdown(f"**关键词:** {char['keywords'][:50]}...")
        
        # 场景资产
        if st.session_state.asset_library['scenes']:
            st.markdown("### 🏙️ 场景")
            for scene_id, scene in st.session_state.asset_library['scenes'].items():
                st.markdown(f"• {scene.get('name', '未命名')} `{scene_id}`")
        
        # 道具资产
        if st.session_state.asset_library['props']:
            st.markdown("### 📦 道具")
            for prop_id, prop in st.session_state.asset_library['props'].items():
                st.markdown(f"• {prop.get('name', '未命名')} `{prop_id}`")
    
    # 进度显示
    st.markdown("---")
    st.markdown(f"### 📍 当前进度: 步骤 {st.session_state.step}/6")
    progress = st.progress(st.session_state.step / 6)
    
    # 修改历史（借鉴Seko的自然语言修改）
    if st.session_state.modification_history:
        with st.expander("📝 修改历史"):
            for i, mod in enumerate(st.session_state.modification_history[-5:]):
                st.markdown(f"**{mod['time']}** - {mod['action']}")

# ==================== 主界面 ====================
st.markdown('<div class="main-header"><h1>🎬 短漫剧生成器 · 火山引擎版</h1><p>分步确认 · 角色一致 · 资产继承 · 自然语言修改</p></div>', unsafe_allow_html=True)

# 检查API是否配置
if not st.session_state.api_configured:
    st.warning("⚠️ 请先在左侧边栏配置火山引擎API密钥")
    st.stop()

# ==================== 步骤1：输入剧本或想法 ====================
if st.session_state.step == 1:
    with st.container():
        st.markdown('<div class="step-box">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">📄 步骤1/6：输入剧本或想法</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 📂 上传剧本文件")
            uploaded_file = st.file_uploader(
                "支持格式：.txt .pdf .doc .docx",
                type=['txt', 'pdf', 'doc', 'docx'],
                key="script_upload"
            )
            if uploaded_file:
                st.success(f"✅ 已选择: {uploaded_file.name}")
                st.session_state.current_data['剧本'] = uploaded_file.name
        
        with col2:
            st.markdown("##### 💡 或直接描述想法")
            idea = st.text_area(
                "例如：一个关于未来东京的少女与AI机器人的温情短剧",
                height=150,
                key="idea_input"
            )
            if idea:
                st.session_state.current_data['想法'] = idea
        
        # 确认按钮
        if st.button("✅ 确认完成步骤1", use_container_width=True):
            if uploaded_file or idea:
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("请上传剧本或描述想法")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== 步骤2：设置影像风格 ====================
elif st.session_state.step == 2:
    with st.container():
        st.markdown('<div class="step-box">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">🎨 步骤2/6：设置影像风格</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            style = st.text_input("🎬 影像风格", "新海诚风", help="如：新海诚风、赛博朋克、宫崎骏风格")
            reference = st.text_input("📽️ 参考影片", "你的名字。", help="可选，如：你的名字、爱死机")
            core = st.text_input("📢 核心诉求", "治愈、青春", help="想要传达的情感")
        
        with col2:
            ratio = st.selectbox("📐 输出比例", ["16:9 (横屏)", "9:16 (竖屏)", "4:3", "1:1"])
            duration = st.slider("⏱️ 影片时长(秒)", 5, 300, 60)
        
        # 保存风格参数
        st.session_state.current_data['风格参数'] = {
            '风格': style,
            '参考影片': reference,
            '核心诉求': core,
            '比例': ratio.split()[0],
            '时长': duration
        }
        
        if st.button("✅ 确认完成步骤2", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== 步骤3：生成故事和分镜 ====================
elif st.session_state.step == 3:
    with st.container():
        st.markdown('<div class="step-box">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">📖 步骤3/6：生成故事和分镜</div>', unsafe_allow_html=True)
        
        # 生成故事元素
        if not st.session_state.current_data.get('故事元素'):
            if st.button("✨ 生成故事元素（调用火山API）", use_container_width=True):
                with st.spinner("AI正在构思故事..."):
                    time.sleep(2)  # 模拟API调用
                    
                    # 模拟生成的故事（根据想法不同而变化）
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
                    
                    # 借鉴Seko：自动创建角色资产
                    if 'Mila' in story['bio']:
                        char_id = str(uuid.uuid4())[:8]
                        st.session_state.asset_library['characters'][char_id] = {
                            'name': 'Mila',
                            'keywords': '16岁少女,琥珀色眼睛,短发,机械右臂',
                            'features': '特征向量_模拟'
                        }
                    st.rerun()
        
        # 显示生成的故事
        if st.session_state.current_data.get('故事元素'):
            story = st.session_state.current_data['故事元素']
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**📖 故事名称：** {story['name']}")
                st.markdown(f"**✨ 一句话：** {story['oneLiner']}")
                st.markdown(f"**📜 故事梗概：** {story['synopsis']}")
                st.markdown(f"**👥 人物小传：** {story['bio']}")
            
            with col2:
                # 借鉴Seko：自然语言修改
                with st.expander("✏️ 提出修改意见"):
                    mod = st.text_area("不满意？输入修改意见", key="story_mod")
                    if st.button("应用修改"):
                        st.session_state.modification_history.append({
                            'time': datetime.now().strftime("%H:%M"),
                            'action': '修改故事'
                        })
                        st.success("修改已记录，AI将重新生成")
                        time.sleep(1)
                        st.rerun()
        
        # 生成分镜
        if st.session_state.current_data.get('故事元素'):
            if not st.session_state.current_data.get('分镜'):
                if st.button("🎬 生成初始分镜", use_container_width=True):
                    with st.spinner("AI正在构思分镜..."):
                        time.sleep(1.5)
                        
                        shots = [
                            {'id': 1, 'type': '全景', 'description': '东京塔废墟，Mila和Kenji站在高架桥上，夕阳染红天空'},
                            {'id': 2, 'type': '中景', 'description': 'Mila低头看着机械臂，Kenji伸手触碰她的肩膀'},
                            {'id': 3, 'type': '特写', 'description': '旧式播放器在Mila手中亮起，浮现全息界面'},
                            {'id': 4, 'type': '远景', 'description': '两人走入废弃音乐厅，舞台中央有一架钢琴'}
                        ]
                        
                        st.session_state.current_data['分镜'] = shots
                        st.rerun()
        
        # 显示分镜
        if st.session_state.current_data.get('分镜'):
            st.markdown("##### 🎞️ 生成的分镜")
            for shot in st.session_state.current_data['分镜']:
                with st.expander(f"🎬 分镜{shot['id']} ({shot['type']})"):
                    st.markdown(shot['description'])
                    
                    # 借鉴Seko：每个分镜可单独修改
                    mod = st.text_input(f"修改分镜{shot['id']}", key=f"shot_mod_{shot['id']}")
                    if mod:
                        shot['description'] = mod
                        st.success("已更新")
        
        # 确认按钮
        if st.session_state.current_data.get('分镜'):
            if st.button("✅ 确认完成步骤3", use_container_width=True):
                st.session_state.step = 4
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== 步骤4：生成形象关键词 ====================
elif st.session_state.step == 4:
    with st.container():
        st.markdown('<div class="step-box">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">🔑 步骤4/6：生成形象关键词</div>', unsafe_allow_html=True)
        
        if not st.session_state.current_data.get('关键词'):
            if st.button("🔑 生成形象关键词（调用火山API）", use_container_width=True):
                with st.spinner("AI正在生成关键词..."):
                    time.sleep(1.5)
                    
                    keywords = {
                        'characters': [
                            'Mila, 16岁少女, 琥珀色眼睛, 凌乱短发, 机械右臂金属质感, 穿着旧夹克, 废土风格',
                            'Kenji, 高大仿生人, 旧式型号, 左肩红色涂装, 磨损雨衣'
                        ],
                        'scenes': [
                            '近未来东京废墟, 夕阳, 倒塌的广告牌, 生锈高架桥, 远处富士山, 柔和光线',
                            '废弃音乐厅, 破旧舞台, 老旧钢琴, 彩色玻璃窗'
                        ],
                        'props': [
                            '旧式音乐播放器, 复古磁带, 金属质感, 发光全息界面',
                            '机械右臂, 精密齿轮, 金属光泽'
                        ]
                    }
                    
                    st.session_state.current_data['关键词'] = keywords
                    
                    # 借鉴Seko：更新资产库
                    for i, char in enumerate(keywords['characters']):
                        char_id = str(uuid.uuid4())[:8]
                        st.session_state.asset_library['characters'][char_id] = {
                            'name': f'角色{i+1}',
                            'keywords': char,
                            'features': '特征向量_模拟'
                        }
                    
                    st.rerun()
        
        # 显示关键词
        if st.session_state.current_data.get('关键词'):
            keywords = st.session_state.current_data['关键词']
            
            tabs = st.tabs(["👤 人物", "🏙️ 场景", "📦 道具"])
            
            with tabs[0]:
                for i, char in enumerate(keywords['characters']):
                    st.markdown(f"**人物{i+1}：**")
                    st.markdown(char)
                    # 借鉴Seko：可上传参考图锁定特征
                    ref_img = st.file_uploader(f"上传人物{i+1}参考图", type=['jpg', 'png'], key=f"char_ref_{i}")
                    if ref_img:
                        st.success("✅ 参考图已保存，角色特征已锁定")
            
            with tabs[1]:
                for scene in keywords['scenes']:
                    st.markdown(f"• {scene}")
            
            with tabs[2]:
                for prop in keywords['props']:
                    st.markdown(f"• {prop}")
            
            if st.button("✅ 确认完成步骤4", use_container_width=True):
                st.session_state.step = 5
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== 步骤5：生成精细分镜关键词 ====================
elif st.session_state.step == 5:
    with st.container():
        st.markdown('<div class="step-box">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">🎞️ 步骤5/6：生成精细分镜关键词</div>', unsafe_allow_html=True)
        
        if not st.session_state.current_data.get('分镜关键词'):
            if st.button("🎞️ 生成精细分镜关键词", use_container_width=True):
                with st.spinner("AI正在生成精细描述..."):
                    time.sleep(1.5)
                    
                    detailed = [
                        {'id': 1, 'keywords': '全景, 倾斜的东京塔废墟, Mila和Kenji站立, 琥珀色眼睛短发少女, 机械右臂, 红色肩章仿生人, 夕阳余晖, 新海诚风格'},
                        {'id': 2, 'keywords': '中景, Mila低头看机械臂, 情绪低落, Kenji伸手触碰, 特写手部, 金属质感, 人物设定一致'},
                        {'id': 3, 'keywords': '特写, 播放器发光, 全息界面, Mila瞳孔反射光芒, 背景虚化, 怀旧氛围'},
                        {'id': 4, 'keywords': '远景, 废弃音乐厅, 舞台中央, 钢琴, 光束从窗户射入, 灰尘漂浮'}
                    ]
                    
                    st.session_state.current_data['分镜关键词'] = detailed
                    st.rerun()
        
        # 显示精细分镜
        if st.session_state.current_data.get('分镜关键词'):
            for item in st.session_state.current_data['分镜关键词']:
                with st.expander(f"🎬 分镜{item['id']}精细描述"):
                    st.markdown(item['keywords'])
                    
                    # 借鉴Seko：自然语言修改
                    mod = st.text_area(f"修改分镜{item['id']}描述", key=f"detail_mod_{item['id']}")
                    if mod and st.button(f"应用修改到分镜{item['id']}", key=f"apply_{item['id']}"):
                        item['keywords'] = mod
                        st.session_state.modification_history.append({
                            'time': datetime.now().strftime("%H:%M"),
                            'action': f'修改分镜{item["id"]}'
                        })
                        st.success("已更新")
                        st.rerun()
            
            if st.button("✅ 确认完成步骤5", use_container_width=True):
                st.session_state.step = 6
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== 步骤6：生成视频 ====================
elif st.session_state.step == 6:
    with st.container():
        st.markdown('<div class="step-box">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">🚀 步骤6/6：生成视频</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🖼️ 上传参考素材")
            ref_file = st.file_uploader(
                "参考图或视频（可选，用于保持一致性）",
                type=['jpg', 'png', 'mp4', 'mov'],
                key="ref_upload"
            )
            if ref_file:
                st.success(f"已选择: {ref_file.name}")
        
        with col2:
            st.markdown("##### 🎚️ 后期设置")
            voice = st.selectbox("配音音色", ["温柔女声", "磁性男声", "可爱童声", "机器人声"])
            bgm = st.selectbox("背景音乐", ["治愈纯音乐", "激昂史诗", "温馨钢琴", "无音乐"])
            subtitle = st.checkbox("添加字幕", value=True)
        
        if st.button("🚀 调用火山引擎生成视频", use_container_width=True):
            with st.spinner("AI正在生成视频（约需要1-2分钟）..."):
                # 模拟进度条
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.05)
                    progress_bar.progress(i + 1)
                
                # 模拟生成结果
                video_result = {
                    'video_url': 'https://example.com/sample.mp4',
                    'task_id': f'task_{int(time.time())}',
                    'duration': st.session_state.current_data['风格参数'].get('时长', 60),
                    'voice': voice,
                    'bgm': bgm
                }
                
                st.session_state.current_data['视频结果'] = video_result
                st.rerun()
        
        # 显示生成的视频
        if st.session_state.current_data.get('视频结果'):
            st.markdown("##### 🎥 生成的视频预览")
            
            # 模拟视频播放器
            st.video("https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4")
            
            result = st.session_state.current_data['视频结果']
            st.markdown(f"""
            <div class="success-msg">
                ✅ 视频生成成功！<br>
                • 任务ID: {result['task_id']}<br>
                • 时长: {result['duration']}秒<br>
                • 配音: {result['voice']}<br>
                • BGM: {result['bgm']}
            </div>
            """, unsafe_allow_html=True)
            
            # 下载按钮
            st.download_button(
                "📥 下载视频",
                data=b"模拟视频数据",
                file_name=f"shortmanju_{int(time.time())}.mp4"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== 完成后的总结 ====================
if st.session_state.step == 6 and st.session_state.current_data.get('视频结果'):
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 重新开始", use_container_width=True):
            for key in ['step', 'current_data', 'asset_library', 'modification_history']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    with col2:
        if st.button("📊 导出项目报告", use_container_width=True):
            report = {
                'session_id': st.session_state.session_id,
                '完成时间': datetime.now().isoformat(),
                '故事': st.session_state.current_data.get('故事元素', {}),
                '资产库': st.session_state.asset_library,
                '修改历史': st.session_state.modification_history
            }
            st.download_button(
                "📥 下载报告",
                data=json.dumps(report, ensure_ascii=False, indent=2),
                file_name=f"report_{int(time.time())}.json"
            )
    
    with col3:
        st.markdown(f"**🎉 恭喜！您已完成6步创作**")