import matplotlib
matplotlib.use('TkAgg')  # macOS 上使用 TkAgg 后端以弹出独立窗口
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

plt.rcParams['font.family'] = ['Arial Unicode MS', 'Heiti SC', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

MAX_STUDENTS = 100
CREDIT_MATH = 5.0
CREDIT_ENGLISH = 3.0
CREDIT_PROGRAMMING = 4.0
TOTAL_CREDITS = CREDIT_MATH + CREDIT_ENGLISH + CREDIT_PROGRAMMING

class Student:
    def __init__(self, student_id, name, math, eng, prog):
        self.student_id = student_id
        self.name = name
        self.math_score = math
        self.english_score = eng
        self.programming_score = prog
        
        # 计算各科绩点
        self.math_gpa = self.calculate_subject_gpa(math)
        self.english_gpa = self.calculate_subject_gpa(eng)
        self.programming_gpa = self.calculate_subject_gpa(prog)
        
        # 计算平均绩点
        self.average_gpa = (self.math_gpa * CREDIT_MATH + self.english_gpa * CREDIT_ENGLISH + self.programming_gpa * CREDIT_PROGRAMMING) / TOTAL_CREDITS

    def calculate_subject_gpa(self, score):
        if score >= 90: 
            return 5.0
        elif score >= 80: 
            return 4.0
        elif score >= 70: 
            return 3.0
        elif score >= 60: 
            return 2.0
        else: 
            return 0.0

    def display(self):
        print(f"{self.student_id:<12}{self.name:<10}{self.math_score:<8.1f}{self.english_score:<8.1f}{self.programming_score:<12.1f}{self.average_gpa:<8.2f}")


class Classroom:
    def __init__(self, class_name="默认班级"):
        self.class_name = class_name
        self.students = []  # 使用列表存储学生

    def get_count(self):
        return len(self.students)

    def add_student(self, student_id, name, math, eng, prog):
        # 1. 检查班级是否已满 
        if len(self.students) >= MAX_STUDENTS:
            print("班级已满，无法添加更多学生！")
            return False

        # 2. 检查学号是否已存在
        for s in self.students:
            if s.student_id == student_id:
                print("学号已存在！")
                return False

        # 3. 添加新学生
        new_student = Student(student_id, name, math, eng, prog)
        self.students.append(new_student)
        return True

    def sort_by_gpa(self):
        self.students.sort(key=lambda s: s.average_gpa, reverse=True)

    def display_all(self):
        print(f"\n========== {self.class_name} 学生成绩表 ==========")
        print(f"{'学号':<12}{'姓名':<10}{'数学':<8}{'英语':<8}{'程序设计':<12}{'平均绩点':<8}")
        print("-" * 60)

        math_sum = 0
        eng_sum = 0
        prog_sum = 0
        gpa_sum = 0
        count = len(self.students)

        for s in self.students:
            s.display()
            math_sum += s.math_score
            eng_sum += s.english_score
            prog_sum += s.programming_score
            gpa_sum += s.average_gpa

        print("-" * 60)
        
        # 计算并显示班级平均分
        if count > 0:
            avg_math = math_sum / count
            avg_eng = eng_sum / count
            avg_prog = prog_sum / count
            avg_gpa = gpa_sum / count
            print(f"{'平均分':<12}{'':<10}{avg_math:<8.1f}{avg_eng:<8.1f}{avg_prog:<12.1f}{avg_gpa:<8.2f}")
        else:
            print("暂无数据")

    def save_to_file(self, filename):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("学号,姓名,数学成绩,英语成绩,程序设计成绩,数学绩点,英语绩点,程序设计绩点,平均绩点\n")
                for s in self.students:
                    line = f"{s.student_id},{s.name},{s.math_score:.1f},{s.english_score:.1f},{s.programming_score:.1f},{s.math_gpa:.2f},{s.english_gpa:.2f},{s.programming_gpa:.2f},{s.average_gpa:.2f}\n"
                    f.write(line)
            print(f"数据已成功保存到文件: {filename}")
        except Exception as e:
            print(f"无法创建文件！错误: {e}")

    def display_statistics(self):
        print("\n========== 成绩分布统计图 ==========")

        math_levels = [0] * 5
        eng_levels = [0] * 5
        prog_levels = [0] * 5
        gpa_levels = [0] * 5  

        for s in self.students:
            # 统计数学
            if s.math_score >= 90: math_levels[0] += 1
            elif s.math_score >= 80: math_levels[1] += 1
            elif s.math_score >= 70: math_levels[2] += 1
            elif s.math_score >= 60: math_levels[3] += 1
            else: math_levels[4] += 1

            # 统计英语
            if s.english_score >= 90: eng_levels[0] += 1
            elif s.english_score >= 80: eng_levels[1] += 1
            elif s.english_score >= 70: eng_levels[2] += 1
            elif s.english_score >= 60: eng_levels[3] += 1
            else: eng_levels[4] += 1

            # 统计程序设计
            if s.programming_score >= 90: prog_levels[0] += 1
            elif s.programming_score >= 80: prog_levels[1] += 1
            elif s.programming_score >= 70: prog_levels[2] += 1
            elif s.programming_score >= 60: prog_levels[3] += 1
            else: prog_levels[4] += 1

            # 统计绩点
            gpa = s.average_gpa
            if gpa >= 4.0: gpa_levels[0] += 1
            elif gpa >= 3.0: gpa_levels[1] += 1
            elif gpa >= 2.0: gpa_levels[2] += 1
            elif gpa >= 1.0: gpa_levels[3] += 1
            else: gpa_levels[4] += 1

        levels_labels = ["90-100", "80-89", "70-79", "60-69", "0-59"]

        # 辅助函数：打印柱状图
        def print_bar_chart(title, counts):
            print(f"\n{title}：")
            for i in range(5):
                # 用字符串乘法画出 '███'
                bar = "█" * counts[i]
                print(f"{levels_labels[i]:<8}|{bar} {counts[i]}人")

        print_bar_chart("高等数学成绩分布", math_levels)
        print_bar_chart("英语成绩分布", eng_levels)
        print_bar_chart("程序设计成绩分布", prog_levels)

        # 显示绩点分布
        print("\n\n========== 绩点分布统计 ==========")
        gpa_labels = ["4.00-5.00", "3.00-3.99", "2.00-2.99", "1.00-1.90", "0.00-0.99"]
        for i in range(5):
            bar = "█" * gpa_levels[i]
            print(f"{gpa_labels[i]:<10}|{bar} {gpa_levels[i]}人")

    def display_charts(self):
        """使用 matplotlib 生成丰富的可视化图表"""
        names = [s.name for s in self.students]
        math_scores  = [s.math_score        for s in self.students]
        eng_scores   = [s.english_score      for s in self.students]
        prog_scores  = [s.programming_score  for s in self.students]
        avg_gpas     = [s.average_gpa        for s in self.students]
        math_gpas    = [s.math_gpa           for s in self.students]
        eng_gpas     = [s.english_gpa        for s in self.students]
        prog_gpas    = [s.programming_gpa    for s in self.students]

        x = np.arange(len(names))
        bar_width = 0.25

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{self.class_name} — 成绩可视化报告', fontsize=16, fontweight='bold')

        # ── 图1：每位学生三门课成绩分组柱状图 ──
        ax1 = axes[0, 0]
        bars1 = ax1.bar(x - bar_width, math_scores,  bar_width, label='高等数学',   color='#4C72B0')
        bars2 = ax1.bar(x,             eng_scores,   bar_width, label='英语',       color='#DD8452')
        bars3 = ax1.bar(x + bar_width, prog_scores,  bar_width, label='程序设计',   color='#55A868')
        ax1.set_title('各学生三门课成绩对比')
        ax1.set_xlabel('学生姓名')
        ax1.set_ylabel('成绩（百分制）')
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, rotation=30, ha='right')
        ax1.set_ylim(0, 110)
        ax1.axhline(y=60, color='red',    linestyle='--', linewidth=0.8, alpha=0.6, label='及格线 60')
        ax1.axhline(y=90, color='purple', linestyle='--', linewidth=0.8, alpha=0.6, label='优秀线 90')
        ax1.legend(fontsize=8)
        ax1.grid(axis='y', alpha=0.3)
        # 标注数值
        for bar in [*bars1, *bars2, *bars3]:
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                     f'{bar.get_height():.0f}', ha='center', va='bottom', fontsize=6)

        # ── 图2：平均绩点排序后的水平条形图 ──
        ax2 = axes[0, 1]
        sorted_pairs = sorted(zip(avg_gpas, names), reverse=True)
        sorted_gpas, sorted_names = zip(*sorted_pairs)
        colors = ['#2ecc71' if g >= 4.0 else '#3498db' if g >= 3.0 else '#e67e22' if g >= 2.0 else '#e74c3c'
                  for g in sorted_gpas]
        bars = ax2.barh(sorted_names, sorted_gpas, color=colors)
        ax2.set_title('学生平均绩点排名（降序）')
        ax2.set_xlabel('平均绩点')
        ax2.set_xlim(0, 5.5)
        ax2.axvline(x=4.0, color='green',  linestyle='--', linewidth=0.8, alpha=0.7, label='优秀 4.0')
        ax2.axvline(x=2.0, color='orange', linestyle='--', linewidth=0.8, alpha=0.7, label='及格 2.0')
        ax2.legend(fontsize=8)
        ax2.grid(axis='x', alpha=0.3)
        for bar, gpa in zip(bars, sorted_gpas):
            ax2.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                     f'{gpa:.2f}', va='center', fontsize=9)

        # ── 图3：三门课各绩点等级人数堆叠柱状图 ──
        ax3 = axes[1, 0]
        gpa_labels_short = ['5.0\n(优)', '4.0\n(良)', '3.0\n(中)', '2.0\n(及格)', '0.0\n(不及格)']
        thresholds = [90, 80, 70, 60, 0]

        def count_levels(scores):
            levels = [0] * 5
            for sc in scores:
                if sc >= 90:   levels[0] += 1
                elif sc >= 80: levels[1] += 1
                elif sc >= 70: levels[2] += 1
                elif sc >= 60: levels[3] += 1
                else:          levels[4] += 1
            return levels

        m_lvl = count_levels(math_scores)
        e_lvl = count_levels(eng_scores)
        p_lvl = count_levels(prog_scores)

        course_labels = ['高等数学', '英语', '程序设计']
        level_colors  = ['#2ecc71', '#3498db', '#f39c12', '#e67e22', '#e74c3c']
        level_names   = ['90-100（优）', '80-89（良）', '70-79（中）', '60-69（及格）', '0-59（不及）']
        bottom_vals = np.zeros(3)
        all_levels = [m_lvl, e_lvl, p_lvl]

        for i in range(5):
            vals = [all_levels[c][i] for c in range(3)]
            ax3.bar(course_labels, vals, bar_width*3, bottom=bottom_vals,
                    color=level_colors[i], label=level_names[i])
            for ci, v in enumerate(vals):
                if v > 0:
                    ax3.text(ci, bottom_vals[ci] + v/2, str(v),
                             ha='center', va='center', fontsize=10, color='white', fontweight='bold')
            bottom_vals += np.array(vals)

        ax3.set_title('三门课各分数段人数堆叠图')
        ax3.set_ylabel('人数')
        ax3.set_ylim(0, len(self.students) + 1)
        ax3.legend(fontsize=8, loc='upper right')
        ax3.grid(axis='y', alpha=0.3)

        # ── 图4：雷达图（各学生综合实力对比，取前5名）──
        ax4 = axes[1, 1]
        ax4.set_title('前5名学生三科绩点雷达图')

        top5 = sorted(self.students, key=lambda s: s.average_gpa, reverse=True)[:5]
        categories = ['高等数学', '英语', '程序设计']
        N = len(categories)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles += angles[:1]  # 闭合

        ax4 = plt.subplot(2, 2, 4, polar=True)
        ax4.set_theta_offset(np.pi / 2)
        ax4.set_theta_direction(-1)
        ax4.set_thetagrids(np.degrees(angles[:-1]), categories)
        ax4.set_ylim(0, 5)
        ax4.set_yticks([1, 2, 3, 4, 5])
        ax4.set_yticklabels(['1', '2', '3', '4', '5'], fontsize=7)

        radar_colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12']
        for idx, s in enumerate(top5):
            values = [s.math_gpa, s.english_gpa, s.programming_gpa]
            values += values[:1]
            ax4.plot(angles, values, 'o-', linewidth=1.5,
                     color=radar_colors[idx], label=s.name)
            ax4.fill(angles, values, alpha=0.1, color=radar_colors[idx])
        ax4.set_title('前5名学生三科绩点雷达图', pad=15)
        ax4.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1), fontsize=9)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig('student_scores_visualization.png', dpi=150, bbox_inches='tight')
        print("可视化图表已保存为: student_scores_visualization.png")
        plt.show()


if __name__ == "__main__":
    # 创建班级
    my_class = Classroom("计算机科学与技术1班")

    print("========== 学生成绩管理系统 ==========")
    print("\n正在初始化学生数据...")

    # 添加10个学生的示例数据
    # 为了保持代码整洁，这里用列表循环添加，和 C++ 效果一样
    initial_data = [
        ("2024001", "张三", 85.5, 92.0, 78.5),
        ("2024002", "李四", 76.0, 88.5, 91.0),
        ("2024003", "王五", 93.0, 93.0, 94.5),
        ("2024004", "赵六", 68.5, 72.0, 65.0),
        ("2024005", "钱七", 88.0, 91.5, 86.0),
        ("2024006", "孙八", 72.5, 68.0, 79.5),
        ("2024007", "周九", 95.0, 87.0, 94.0),
        ("2024008", "吴十", 81.0, 76.5, 82.0),
        ("2024009", "郑十一", 64.0, 70.0, 73.5),
        ("2024010", "王十二", 89.5, 94.0, 88.5)
    ]

    for data in initial_data:
        my_class.add_student(*data) # *data 是解包参数

    print(f"数据初始化完成！当前班级有 {my_class.get_count()} 名学生。\n")

    # 显示原始数据
    print("\n【原始数据】")
    my_class.display_all()

    # 按绩点排序
    print("\n\n正在按平均绩点排序...")
    my_class.sort_by_gpa()

    # 显示排序后的数据
    print("\n【排序后数据（按平均绩点降序）】")
    my_class.display_all()

    # 显示统计图表
    print("\n")
    my_class.display_statistics()

    # 输出到文件
    my_class.save_to_file("student_scores.csv")

    # 可视化图表
    print("\n正在生成可视化图表...")
    my_class.display_charts()

    print("\n\n========== 程序运行完成 ==========")
    input("按任意键退出...")