import matplotlib.pyplot as plt
import csv
import datetime

# 任务1：统计所有车辆中，各类车的占比，绘制成饼图

vehicle_count = {}  # 一个空字典，用来累计计数

with open("WIMData.csv", "r", newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        vehicle_type = row['VehicleType']
        if vehicle_type in vehicle_count:
            vehicle_count[vehicle_type] += 1 
        else:
            vehicle_count[vehicle_type] = 1  

labels = list(vehicle_count.keys())    # 将dict_keys转换成列表
sizes = list(vehicle_count.values())   # 将dict_values转换成列表

plt.pie(sizes, labels=labels, autopct='%1.1f%%')
plt.title('Vehicle Type Distribution')
plt.savefig('vehicle_distribution.png')
plt.close()

# 任务2 统计每个车道中，各类车的占比，为每个车道绘制一个饼图

lane_vehicle_count = {}  # 初始化（在with之前）

with open("WIMData.csv", "r", newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # 检查这个车道是否已经在lane_vehicle_count中
        lane = row['Lane']
        vehicle_type = row['VehicleType']
        if lane not in lane_vehicle_count:
            lane_vehicle_count[lane] = {}  # 为这个车道初始化一个空字典
        
        # 在这个车道的字典中进行计数
        if vehicle_type in lane_vehicle_count[lane]:
            lane_vehicle_count[lane][vehicle_type] += 1
        else:
            lane_vehicle_count[lane][vehicle_type] = 1


for lane in lane_vehicle_count:
    labels = list(lane_vehicle_count[lane].keys())
    sizes = list(lane_vehicle_count[lane].values())
    plt.figure()  # 为每个车道创建一个新的图表
    plt.pie(sizes, labels=labels, autopct='%1.1f%%')
    plt.title(f'Lane {lane} Vehicle Distribution')
    plt.savefig(f'lane_{lane}_vehicle_distribution.png')
    plt.close()


# 以下是任务3 统计1~3车道为方向1，4~6车道为方向2 比较两个方向上通过的车总数和每种车型的数量是否相同

direction_vehicle_count = {}  # 初始化

with open("WIMData.csv", "r", newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        lane = row['Lane']
        vehicle_type = row['VehicleType']
        
        # 判断方向
        if lane in ['1', '2', '3']:
            direction = 'direction1'
        else:
            direction = 'direction2'

        if direction not in direction_vehicle_count:
            direction_vehicle_count[direction] = {}
        
        # 在这个车道的字典中进行计数
        if vehicle_type in direction_vehicle_count[direction]:
            direction_vehicle_count[direction][vehicle_type] += 1
        else:
            direction_vehicle_count[direction][vehicle_type] = 1

print("\n========== 方向对比分析 ==========")
print(f"{'车型':<5} {'方向1':<10} {'方向2':<10}")
print("-" * 30)

# 获取所有的车型（合并两个方向的车型）
all_vehicle_types = set(direction_vehicle_count['direction1'].keys()) | set(direction_vehicle_count['direction2'].keys())

for vehicle_type in sorted(all_vehicle_types):
    count1 = direction_vehicle_count['direction1'].get(vehicle_type, 0)
    count2 = direction_vehicle_count['direction2'].get(vehicle_type, 0)
    print(f"{vehicle_type:<5} {count1:<10} {count2:<10}")

# 总数
total1 = sum(direction_vehicle_count['direction1'].values())
total2 = sum(direction_vehicle_count['direction2'].values())
print("-" * 30)
print(f"{'总计':<5} {total1:<10} {total2:<10}")

# 以下是任务4 计算每个车道的车重平均值、最大值、最小值 绘制点线图

lane_weights = {}  # 初始化
with open("WIMData.csv", "r", newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        lane = row['Lane']
        weight = float(row['TotalWeight'])
        
        if lane not in lane_weights:
            lane_weights[lane] = []
        
        lane_weights[lane].append(weight)

lane_stats = {}  # 存储统计结果

for lane in lane_weights:
    weights = lane_weights[lane]
    lane_stats[lane] = {
        'avg': sum(weights) / len(weights),
        'max': max(weights),
        'min': min(weights)
    }

# 准备数据
lanes = sorted(lane_stats.keys())  # 排序车道号，确保顺序为 1,2,3,4,5,6
avg_weights = [lane_stats[lane]['avg'] for lane in lanes]
max_weights = [lane_stats[lane]['max'] for lane in lanes]
min_weights = [lane_stats[lane]['min'] for lane in lanes]

plt.figure(figsize=(10, 6))
plt.plot(lanes, avg_weights, marker='o', label='Average Weight')
plt.plot(lanes, max_weights, marker='s', label='Max Weight')
plt.plot(lanes, min_weights, marker='^', label='Min Weight')
plt.xlabel('Lane')
plt.ylabel('Weight (kg)')
plt.title('Vehicle Weight Statistics by Lane')
plt.legend()
plt.grid(True)
plt.savefig('lane_weight_analysis.png')
plt.close()

# 以下是任务5 选择具有完整数据的某天（24小时完整） 统计每小时车流量，绘制点线图（横坐标：小时0~23，纵坐标：车流量）

date_hours = {}  # 存储每一天的小时集合

with open("WIMData.csv", "r", newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        datetime_str = row['PassTime']
        date = datetime_str.split()[0]
        hour = int(datetime_str.split()[1].split(':')[0])
        
        # 检查这一天是否已经在字典中
        if date not in date_hours:
            date_hours[date] = set()  # 用set来存储小时，避免重复
        
        # 把这个小时加入到这一天的集合中
        date_hours[date].add(hour)

# 找出有24个小时的日期
complete_dates = [date for date, hours in date_hours.items() if len(hours) == 24]
print(f"完整数据的日期：{complete_dates}")

# 如果有完整日期，选择第一个
if complete_dates:
    selected_date = complete_dates[0]
    print(f"选择的分析日期：{selected_date}")
else:
    print("没有找到完整的24小时数据")

# 统计所选日期每小时的车流量
hourly_traffic = {}  # 存储每小时的车辆数

with open("WIMData.csv", "r", newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        datetime_str = row['PassTime']
        date = datetime_str.split()[0]
        hour = int(datetime_str.split()[1].split(':')[0])
        
        # 只统计所选日期的数据
        if date == selected_date:
            if hour not in hourly_traffic:
                hourly_traffic[hour] = 0
            hourly_traffic[hour] += 1

# 确保24个小时都有数据（没有车辆的小时设为0）
hours = list(range(24))  # 0到23
traffic = [hourly_traffic.get(h, 0) for h in hours]

# 绘制车流量点线图
plt.figure(figsize=(12, 6))
plt.plot(hours, traffic, marker='o', color='blue', linewidth=2)
plt.xlabel('Hour')
plt.ylabel('Traffic Volume')
plt.title(f'Hourly Traffic Volume on {selected_date}')
plt.xticks(hours)  # 确保横坐标显示每个小时
plt.grid(True)
plt.savefig('hourly_traffic.png')
plt.close()
print("车流量点线图已保存为 hourly_traffic.png")


# 任务7（选做）：对比工作日和双休日的车流量变化规律 按车型统计工作日和双休日的车流量，分析规律
import datetime

# 统计工作日和双休日的每小时车流量
weekday_hourly = {}  # 工作日每小时车流量
weekend_hourly = {}  # 双休日每小时车流量

# 初始化0-23小时
for h in range(24):
    weekday_hourly[h] = 0
    weekend_hourly[h] = 0

with open("WIMData.csv", "r", newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        datetime_str = row['PassTime']
        date = datetime_str.split()[0]
        hour = int(datetime_str.split()[1].split(':')[0])
        
        # 判断是周几（0=周一，6=周日）
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
        day_of_week = date_obj.weekday()  # 0-4是周一到周五(工作日)，5-6是周六日(双休日)
        
        if day_of_week < 5:  # 工作日
            weekday_hourly[hour] += 1
        else:  # 双休日
            weekend_hourly[hour] += 1

# 绘制工作日vs双休日的对比图
hours = list(range(24))
weekday_traffic = [weekday_hourly[h] for h in hours]
weekend_traffic = [weekend_hourly[h] for h in hours]

plt.figure(figsize=(12, 6))
plt.plot(hours, weekday_traffic, marker='o', label='Weekday', linewidth=2)
plt.plot(hours, weekend_traffic, marker='s', label='Weekend', linewidth=2)
plt.xlabel('Hour')
plt.ylabel('Traffic Volume')
plt.title('Traffic Comparison: Weekday vs Weekend')
plt.xticks(hours)
plt.legend()
plt.grid(True)
plt.savefig('weekday_vs_weekend_traffic.png')
plt.close()
print("工作日vs双休日对比图已保存为 weekday_vs_weekend_traffic.png")

# 按车型统计每小时车流量
# 统计各车型在工作日和双休日的每小时车流量
vehicle_weekday_hourly = {}  # 工作日各车型每小时
vehicle_weekend_hourly = {}  # 双休日各车型每小时

with open("WIMData.csv", "r", newline='', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        datetime_str = row['PassTime']
        date = datetime_str.split()[0]
        hour = int(datetime_str.split()[1].split(':')[0])
        vehicle_type = row['VehicleType']
        
        # 判断是周几
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
        day_of_week = date_obj.weekday()
        
        # 初始化字典
        if vehicle_type not in vehicle_weekday_hourly:
            vehicle_weekday_hourly[vehicle_type] = {h: 0 for h in range(24)}
        if vehicle_type not in vehicle_weekend_hourly:
            vehicle_weekend_hourly[vehicle_type] = {h: 0 for h in range(24)}
        
        if day_of_week < 5:  # 工作日
            vehicle_weekday_hourly[vehicle_type][hour] += 1
        else:  # 双休日
            vehicle_weekend_hourly[vehicle_type][hour] += 1

# 绘制各车型的工作日vs双休日对比
# 选择最常见的几种车型（A、B、D、E、F）来绘制
selected_vehicles = ['A', 'B', 'D', 'E', 'F']

plt.figure(figsize=(14, 8))
for vehicle_type in selected_vehicles:
    if vehicle_type in vehicle_weekday_hourly:
        weekday_data = [vehicle_weekday_hourly[vehicle_type].get(h, 0) for h in hours]
        weekend_data = [vehicle_weekend_hourly[vehicle_type].get(h, 0) for h in hours]
        
        # 绘制该车型的工作日数据
        plt.plot(hours, weekday_data, marker='o', label=f'Vehicle {vehicle_type} (Weekday)', linewidth=1.5)

plt.xlabel('Hour')
plt.ylabel('Traffic Volume')
plt.title('Weekday Traffic by Vehicle Type')
plt.xticks(hours)
plt.legend()
plt.grid(True)
plt.savefig('vehicle_weekday_traffic.png')
plt.close()

# 绘制双休日的各车型对比
plt.figure(figsize=(14, 8))
for vehicle_type in selected_vehicles:
    if vehicle_type in vehicle_weekend_hourly:
        weekend_data = [vehicle_weekend_hourly[vehicle_type].get(h, 0) for h in hours]
        
        # 绘制该车型的双休日数据
        plt.plot(hours, weekend_data, marker='s', label=f'Vehicle {vehicle_type} (Weekend)', linewidth=1.5)

plt.xlabel('Hour')
plt.ylabel('Traffic Volume')
plt.title('Weekend Traffic by Vehicle Type')
plt.xticks(hours)
plt.legend()
plt.grid(True)
plt.savefig('vehicle_weekend_traffic.png')
plt.close()

print("各车型工作日流量图已保存为 vehicle_weekday_traffic.png")
print("各车型双休日流量图已保存为 vehicle_weekend_traffic.png")
print("\n分析完成！所有图表和数据已生成。")