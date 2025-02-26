import streamlit as st
from supabase import create_client, Client
import hashlib
import datetime
import pandas as pd


# Supabase 配置（替换为您的 Supabase 项目 URL 和 anon key）
SUPABASE_URL = "https://aliyuysjhhwxylknkxjx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFsaXl1eXNqaGh3eHlsa25reGp4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MDUzOTQzNywiZXhwIjoyMDU2MTE1NDM3fQ._toegb3-dNMSbEKJohz5YyS7PMpngjrKP5y-cpzqq2I"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 计算哈希值
def generate_hash(user_id, eggs, timestamp):
    data_string = f"{user_id}{eggs}{timestamp}"
    return hashlib.sha256(data_string.encode()).hexdigest()

# 用户注册
def register(email, password):
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            user_id = response.user.id
            supabase.table('users').insert({
                'user_id': user_id,
                'username': email,
                'role': 'user'
            }).execute()
            st.success("注册成功！请登录。")
        else:
            st.error(f"注册失败: {response.error.message}")
    except Exception as e:
        st.error(f"注册失败: {str(e)}")

# 用户登录
def login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            user_id = response.user.id
            role_response = supabase.table('users').select('role').eq('user_id', user_id).execute()
            role = role_response.data[0]['role'] if role_response.data else 'user'
            log_action(user_id, "登录")
            return user_id, role
        else:
            st.error(f"登录失败: {response.error.message}")
            return None, None
    except Exception as e:
        st.error(f"登录失败: {str(e)}")
        return None, None

# 记录消费
def record_eggs(user_id, eggs):
    timestamp = datetime.datetime.now().isoformat()
    record_hash = generate_hash(user_id, eggs, timestamp)
    try:
        supabase.table('consumption').insert({
            'user_id': user_id,
            'eggs': eggs,
            'timestamp': timestamp,
            'hash': record_hash
        }).execute()
        log_action(user_id, f"记录消费: {eggs} 个鸡蛋")
        st.success("记录成功！")
    except Exception as e:
        st.error(f"记录失败: {str(e)}")

# 查看个人记录
def view_personal_records(user_id):
    try:
        response = supabase.table('consumption').select('eggs', 'timestamp', 'hash').eq('user_id', user_id).execute()
        records = response.data
        return pd.DataFrame(records, columns=["鸡蛋数量", "时间", "哈希值"])
    except Exception as e:
        st.error(f"获取记录失败: {str(e)}")
        return pd.DataFrame()

# 查看所有记录（公开统计）
def view_all_records():
    try:
        # 使用 Supabase 的外键关系语法
        response = supabase.table('consumption').select('eggs, timestamp, users!inner(username)').execute()
        records = response.data
        # 调整返回数据格式
        processed_records = [
            {'用户名': record['users']['username'], '鸡蛋数量': record['eggs'], '时间': record['timestamp']}
            for record in records
        ]
        return pd.DataFrame(processed_records, columns=['用户名', '鸡蛋数量', '时间'])
    except Exception as e:
        st.error(f"获取记录失败: {str(e)}")
        return pd.DataFrame()


# 记录审计日志
def log_action(user_id, action):
    timestamp = datetime.datetime.now().isoformat()
    try:
        supabase.table('audit_log').insert({
            'user_id': user_id,
            'action': action,
            'timestamp': timestamp
        }).execute()
    except Exception as e:
        st.error(f"记录审计日志失败: {str(e)}")

# 主程序
def main():
    st.title("鸡蛋消费记录系统")

    # 会话状态管理
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'role' not in st.session_state:
        st.session_state.role = None

    # 未登录时显示登录/注册界面
    if not st.session_state.user_id:
        menu = ["登录", "注册"]
        choice = st.sidebar.selectbox("选择操作", menu)

        if choice == "注册":
            st.subheader("用户注册")
            email = st.text_input("邮箱")
            password = st.text_input("密码", type="password")
            if st.button("注册"):
                register(email, password)
        
        elif choice == "登录":
            st.subheader("用户登录")
            email = st.text_input("邮箱")
            password = st.text_input("密码", type="password")
            if st.button("登录"):
                user_id, role = login(email, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.role = role

    # 已登录时显示功能界面
    else:
        st.sidebar.write(f"已登录用户: {st.session_state.user_id}")
        if st.sidebar.button("退出"):
            log_action(st.session_state.user_id, "登出")
            st.session_state.user_id = None
            st.session_state.role = None
            st.experimental_rerun()

        menu = ["记录消费", "查看个人记录", "查看整体统计"]
        if st.session_state.role == "admin":
            menu.append("查看所有记录")
        choice = st.sidebar.selectbox("选择功能", menu)

        if choice == "记录消费":
            st.subheader("记录鸡蛋消费")
            eggs = st.number_input("消费的鸡蛋数量", min_value=1, step=1)
            if st.button("提交"):
                record_eggs(st.session_state.user_id, eggs)

        elif choice == "查看个人记录":
            st.subheader("我的消费记录")
            records = view_personal_records(st.session_state.user_id)
            st.dataframe(records)

        elif choice == "查看整体统计":
            st.subheader("整体消费统计")
            all_records = view_all_records()
            st.dataframe(all_records)
            if not all_records.empty:
                st.write("总鸡蛋消费量:", all_records["鸡蛋数量"].sum())

        elif choice == "查看所有记录" and st.session_state.role == "admin":
            st.subheader("所有用户记录（管理员）")
            all_records = view_all_records()
            st.dataframe(all_records)

if __name__ == "__main__":
    main()
