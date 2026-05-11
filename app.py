import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import requests
import math

# --- دالة لجلب توقعات الطقس الساعية (Hourly Forecast) ---
def get_hourly_weather(lat, lon, hours):
    try:
        # طلب التوقعات الساعية، مع تحديد وحدة السرعة لتكون متر/ثانية مباشرة
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=windspeed_10m,winddirection_10m&windspeed_unit=ms&forecast_days=14"
        response = requests.get(url)
        data = response.json()
        
        # أخذ البيانات على عدد ساعات المحاكاة المطلوبة
        wind_speeds = data['hourly']['windspeed_10m'][:hours]
        wind_dirs = data['hourly']['winddirection_10m'][:hours]
        
        wind_x = np.zeros(hours)
        wind_y = np.zeros(hours)
        
        # تحويل سرعة واتجاه كل ساعة إلى متجهات (X, Y)
        for i in range(hours):
            speed = wind_speeds[i]
            direction = wind_dirs[i]
            rad = math.radians(direction)
            wind_x[i] = -speed * math.sin(rad)
            wind_y[i] = -speed * math.cos(rad)
            
        return wind_x, wind_y, wind_speeds, wind_dirs
    except Exception as e:
        st.error("⚠️ حدث خطأ أثناء جلب بيانات الطقس. يتم استخدام قيم صفرية.")
        return np.zeros(hours), np.zeros(hours), np.zeros(hours), np.zeros(hours)

# --- إعدادات واجهة التطبيق ---
st.set_page_config(page_title="محاكاة بقعة الزيت الديناميكية", layout="wide")
st.title("🌊 محاكاة مسار الزيت الديناميكية (توقعات ساعية 🌤️⏱️)")
st.write("المسار الآن يتغير وينحني ديناميكياً بناءً على التغير الزمني لاتجاه وسرعة الرياح لكل ساعة قادمة.")

# --- القائمة الجانبية للتحكم ---
st.sidebar.header("📍 إحداثيات الموقع")
lat = st.sidebar.number_input("خط العرض (Latitude)", value=29.11, format="%.4f")
lon = st.sidebar.number_input("خط الطول (Longitude)", value=48.11, format="%.4f")

st.sidebar.markdown("---")
st.sidebar.header("🛢️ خصائص التسرب")
oil_types = {
    "زيت خفيف (مثل الديزل)": {"diffusion": 200.0, "color": "orange"},
    "زيت متوسط (نفط خام)": {"diffusion": 100.0, "color": "saddlebrown"},
    "زيت ثقيل (وقود سفن)": {"diffusion": 30.0, "color": "black"}
}

selected_oil = st.sidebar.selectbox("اختر نوع الزيت:", list(oil_types.keys()))
diffusion_rate = oil_types[selected_oil]["diffusion"]
oil_color = oil_types[selected_oil]["color"]

st.sidebar.markdown("---")
st.sidebar.header("🌊 إعدادات التيار المائي")
current_x = st.sidebar.slider("سرعة التيار (شرق/غرب)", -2.0, 2.0, 0.5)
current_y = st.sidebar.slider("سرعة التيار (شمال/جنوب)", -2.0, 2.0, 0.1)

time_steps = st.sidebar.slider("مدة المحاكاة (بالساعات)", 10, 300, 100)

# --- جلب التوقعات الساعية ---
wind_x_arr, wind_y_arr, speeds_arr, dirs_arr = get_hourly_weather(lat, lon, time_steps)

# عرض حالة الطقس كمتوسط للتوضيح
avg_speed = np.mean(speeds_arr)
st.info(f"📊 *متوسط سرعة الرياح المتوقعة خلال {time_steps} ساعة:* {avg_speed:.2f} متر/ثانية. (المحاكاة تقرأ التغيرات ساعة بساعة)")

# --- الحسابات الرياضية للمحاكاة (تحديث ديناميكي داخل الدورة) ---
num_particles = 1000
dt = 3600
wind_factor = 0.03

v_current = np.array([current_x, current_y])
positions = np.zeros((time_steps, num_particles, 2))

# المحاكاة تتغير كل ساعة بناءً على طقس تلك الساعة
for t in range(1, time_steps):
    # استخدام رياح الساعة المحددة
    current_wind_v = np.array([wind_x_arr[t], wind_y_arr[t]])
    
    # حساب الانجراف لهذه الساعة فقط
    v_advection = v_current + (wind_factor * current_wind_v)
    
    # حساب الانتشار
    random_walk = np.random.normal(0, np.sqrt(2 * diffusion_rate * dt), (num_particles, 2))
    
    # تحديث المواقع
    positions[t] = positions[t-1] + (v_advection * dt) + random_walk

# --- رسم النتائج ---
fig, ax = plt.subplots(figsize=(10, 6))

# رسم مسار الجزيئات
for t in range(0, time_steps, max(1, time_steps//10)): 
    ax.scatter(positions[t, :, 0], positions[t, :, 1], s=2, alpha=0.5, color=oil_color)

ax.scatter(0, 0, color='red', marker='X', s=150, label='نقطة التسرب (0,0)')
ax.set_title(f'المسار الديناميكي لـ ({selected_oil}) بناءً على التوقعات الساعية')
ax.set_xlabel('المسافة شرق/غرب (أمتار)')
ax.set_ylabel('المسافة شمال/جنوب (أمتار)')
ax.axhline(0, color='black', linewidth=0.5, linestyle='--')
ax.axvline(0, color='black', linewidth=0.5, linestyle='--')
ax.legend()
ax.grid(True, linestyle=':', alpha=0.7)

st.pyplot(fig)