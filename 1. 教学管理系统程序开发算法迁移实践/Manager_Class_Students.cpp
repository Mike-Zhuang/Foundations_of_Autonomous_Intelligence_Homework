#include <iostream>
#include <fstream>
#include <iomanip>
#include <cstring>
#include <string>
using namespace std;


const int MAX_STUDENTS = 100; 
const int NAME_LENGTH = 50;
const int ID_LENGTH = 20;
const double CREDIT_MATH = 5.0;
const double CREDIT_ENGLISH = 3.0;
const double CREDIT_PROGRAMMING = 4.0;
const double TOTAL_CREDITS = CREDIT_MATH + CREDIT_ENGLISH + CREDIT_PROGRAMMING;

// 学生类
class Student {
private:
    char studentId[ID_LENGTH];
    char name[NAME_LENGTH];
    double mathScore;
    double englishScore;
    double programmingScore;
    double mathGpa;
    double englishGpa;
    double programmingGpa;
    double averageGpa;

    // 计算单科绩点（100分制转4分制）
    double calculateSubjectGpa(double score) {
        if (score >= 90) return 5.0;
        else if (score >= 80) return 4.0;
        else if (score >= 70) return 3.0;
        else if (score >= 60) return 2.0;
        else return 0.0;
    }

public:
    // 构造函数
    Student() {
        studentId[0] = '\0';
        name[0] = '\0';
        mathScore = 0;
        englishScore = 0;
        programmingScore = 0;
        mathGpa = 0;
        englishGpa = 0;
        programmingGpa = 0;
        averageGpa = 0;
    }

    // 设置学生信息
    void setInfo(const char* id, const char* n, double math, double eng, double prog) {
        strcpy(studentId, id);
        strcpy(name, n);
        mathScore = math;
        englishScore = eng;
        programmingScore = prog;

        // 计算各科绩点
        mathGpa = calculateSubjectGpa(mathScore);
        englishGpa = calculateSubjectGpa(englishScore);
        programmingGpa = calculateSubjectGpa(programmingScore);

        // 计算平均绩点（加权平均）
        averageGpa = (mathGpa * CREDIT_MATH + englishGpa * CREDIT_ENGLISH +
            programmingGpa * CREDIT_PROGRAMMING) / TOTAL_CREDITS;
    }

    // 获取学生信息
    const char* getId() const { return studentId; }
    const char* getName() const { return name; }
    double getMathScore() const { return mathScore; }
    double getEnglishScore() const { return englishScore; }
    double getProgrammingScore() const { return programmingScore; }
    double getMathGpa() const { return mathGpa; }
    double getEnglishGpa() const { return englishGpa; }
    double getProgrammingGpa() const { return programmingGpa; }
    double getAverageGpa() const { return averageGpa; }

    // 显示学生信息
    void display() const {
        cout << left << setw(12) << studentId
            << setw(10) << name
            << setw(8) << fixed << setprecision(1) << mathScore
            << setw(8) << englishScore
            << setw(12) << programmingScore
            << setw(8) << setprecision(2) << averageGpa << endl;
    }

    // 比较平均绩点（用于排序）
    bool hasHigherGpaThan(const Student& other) const {
        return averageGpa > other.averageGpa;
    }
};

// 班级类
class Class {
private:
    Student students[MAX_STUDENTS];
    int studentCount;
    char className[NAME_LENGTH];

public:
    // 构造函数
    Class(const char* name = "默认班级") {
        strcpy(className, name);
        studentCount = 0;
    }

    // 添加学生
    bool addStudent(const char* id, const char* name, double math, double eng, double prog) {
        if (studentCount >= MAX_STUDENTS) {
            cout << "班级已满，无法添加更多学生！" << endl;
            return false;
        }

        // 检查学号是否已存在
        for (int i = 0; i < studentCount; i++) {
            if (strcmp(students[i].getId(), id) == 0) {
                cout << "学号已存在！" << endl;
                return false;
            }
        }

        students[studentCount].setInfo(id, name, math, eng, prog);
        studentCount++;
        return true;
    }

    // 获取学生数量
    int getCount() const { return studentCount; }

    // 获取学生（用于排序和访问）
    Student* getStudents() { return students; }
    const Student* getStudents() const { return students; }

    // 简单选择排序（按平均绩点降序）
    void sortByGpa() {
        for (int i = 0; i < studentCount - 1; i++) {
            int maxIndex = i;
            for (int j = i + 1; j < studentCount; j++) {
                if (students[j].getAverageGpa() > students[maxIndex].getAverageGpa()) {
                    maxIndex = j;
                }
            }
            if (maxIndex != i) {
                // 交换学生
                Student temp = students[i];
                students[i] = students[maxIndex];
                students[maxIndex] = temp;
            }
        }
    }

    // 显示所有学生
    void displayAll() const {
        cout << "\n========== " << className << " 学生成绩表 ==========" << endl;
        cout << left << setw(12) << "学号"
            << setw(10) << "姓名"
            << setw(8) << "数学"
            << setw(8) << "英语"
            << setw(12) << "程序设计"
            << setw(8) << "平均绩点" << endl;
        cout << string(58, '-') << endl;

        double mathSum = 0, engSum = 0, progSum = 0, gpaSum = 0;

        for (int i = 0; i < studentCount; i++) {
            students[i].display();
            mathSum += students[i].getMathScore();
            engSum += students[i].getEnglishScore();
            progSum += students[i].getProgrammingScore();
            gpaSum += students[i].getAverageGpa();
        }

        cout << string(58, '-') << endl;
        cout << left << setw(12) << "平均分"
            << setw(10) << ""
            << setw(8) << fixed << setprecision(1) << (mathSum / studentCount)
            << setw(8) << (engSum / studentCount)
            << setw(12) << (progSum / studentCount)
            << setw(8) << setprecision(2) << (gpaSum / studentCount) << endl;
    }

    // 输出到文件
    void saveToFile(const char* filename) const {
        ofstream outFile(filename);
        if (!outFile) {
            cout << "无法创建文件！" << endl;
            return;
        }

        outFile << "学号,姓名,数学成绩,英语成绩,程序设计成绩,数学绩点,英语绩点,程序设计绩点,平均绩点" << endl;

        for (int i = 0; i < studentCount; i++) {
            outFile << students[i].getId() << ","
                << students[i].getName() << ","
                << fixed << setprecision(1) << students[i].getMathScore() << ","
                << students[i].getEnglishScore() << ","
                << students[i].getProgrammingScore() << ","
                << setprecision(2) << students[i].getMathGpa() << ","
                << students[i].getEnglishGpa() << ","
                << students[i].getProgrammingGpa() << ","
                << students[i].getAverageGpa() << endl;
        }

        outFile.close();
        cout << "数据已成功保存到文件: " << filename << endl;
    }

    // 显示统计图表
    void displayStatistics() const {
        cout << "\n========== 成绩分布统计图 ==========" << endl;

        // 统计各分数段人数
        int mathLevels[5] = { 0 };  // 90-100, 80-89, 70-79, 60-69, 0-59
        int engLevels[5] = { 0 };
        int progLevels[5] = { 0 };

        for (int i = 0; i < studentCount; i++) {
            // 数学
            int mathScore = students[i].getMathScore();
            if (mathScore >= 90) mathLevels[0]++;
            else if (mathScore >= 80) mathLevels[1]++;
            else if (mathScore >= 70) mathLevels[2]++;
            else if (mathScore >= 60) mathLevels[3]++;
            else mathLevels[4]++;

            // 英语
            int engScore = students[i].getEnglishScore();
            if (engScore >= 90) engLevels[0]++;
            else if (engScore >= 80) engLevels[1]++;
            else if (engScore >= 70) engLevels[2]++;
            else if (engScore >= 60) engLevels[3]++;
            else engLevels[4]++;

            // 程序设计
            int progScore = students[i].getProgrammingScore();
            if (progScore >= 90) progLevels[0]++;
            else if (progScore >= 80) progLevels[1]++;
            else if (progScore >= 70) progLevels[2]++;
            else if (progScore >= 60) progLevels[3]++;
            else progLevels[4]++;
        }

        // 显示柱状图
        const char* levels[] = { "90-100", "80-89", "70-79", "60-69", "0-59" };

        cout << "\n高等数学成绩分布：" << endl;
        for (int i = 0; i < 5; i++) {
            cout << left << setw(8) << levels[i] << "|";
            for (int j = 0; j < mathLevels[i]; j++) {
                cout << "█";
            }
            cout << " " << mathLevels[i] << "人" << endl;
        }

        cout << "\n英语成绩分布：" << endl;
        for (int i = 0; i < 5; i++) {
            cout << left << setw(8) << levels[i] << "|";
            for (int j = 0; j < engLevels[i]; j++) {
                cout << "█";
            }
            cout << " " << engLevels[i] << "人" << endl;
        }

        cout << "\n程序设计成绩分布：" << endl;
        for (int i = 0; i < 5; i++) {
            cout << left << setw(8) << levels[i] << "|";
            for (int j = 0; j < progLevels[i]; j++) {
                cout << "█";
            }
            cout << " " << progLevels[i] << "人" << endl;
        }

        // 显示绩点分布
        cout << "\n\n========== 绩点分布统计 ==========" << endl;
        int gpaLevels[5] = { 0 };  // 4.0, 3.0-3.9, 2.0-2.9, 1.0-1.9, 0-0.9

        for (int i = 0; i < studentCount; i++) {
            double gpa = students[i].getAverageGpa();
            if (gpa >= 4.0) gpaLevels[0]++;
            else if (gpa >= 3.0) gpaLevels[1]++;
            else if (gpa >= 2.0) gpaLevels[2]++;
            else if (gpa >= 1.0) gpaLevels[3]++;
            else gpaLevels[4]++;
        }

        const char* gpaLabels[] = { "4.00-5.00", "3.00-3.99", "2.00-2.99", "1.00-1.90", "0.00-0.99" };
        for (int i = 0; i < 5; i++) {
            cout << left << setw(10) << gpaLabels[i] << "|";
            for (int j = 0; j < gpaLevels[i]; j++) {
                cout << "█";
            }
            cout << " " << gpaLevels[i] << "人" << endl;
        }
    }
};

// 主函数
int main() {
    // 创建班级
    Class myClass("计算机科学与技术1班");

    cout << "========== 学生成绩管理系统 ==========" << endl;

    // 初始化学生数据（10个学生）
    cout << "\n正在初始化学生数据..." << endl;

    // 添加10个学生的示例数据
    myClass.addStudent("2024001", "张三", 85.5, 92.0, 78.5);
    myClass.addStudent("2024002", "李四", 76.0, 88.5, 91.0);
    myClass.addStudent("2024003", "王五", 93.0, 93.0, 94.5);
    myClass.addStudent("2024004", "赵六", 68.5, 72.0, 65.0);
    myClass.addStudent("2024005", "钱七", 88.0, 91.5, 86.0);
    myClass.addStudent("2024006", "孙八", 72.5, 68.0, 79.5);
    myClass.addStudent("2024007", "周九", 95.0, 87.0, 94.0);
    myClass.addStudent("2024008", "吴十", 81.0, 76.5, 82.0);
    myClass.addStudent("2024009", "郑十一", 64.0, 70.0, 73.5);
    myClass.addStudent("2024010", "王十二", 89.5, 94.0, 88.5);

    cout << "数据初始化完成！当前班级有 " << myClass.getCount() << " 名学生。\n" << endl;

    // 显示原始数据
    cout << "\n【原始数据】" << endl;
    myClass.displayAll();

    // 按绩点排序
    cout << "\n\n正在按平均绩点排序..." << endl;
    myClass.sortByGpa();

    // 显示排序后的数据
    cout << "\n【排序后数据（按平均绩点降序）】" << endl;
    myClass.displayAll();

    // 显示统计图表
    cout << "\n";
    myClass.displayStatistics();

    // 输出到文件
    myClass.saveToFile("student_scores.csv");

    cout << "\n\n========== 程序运行完成 ==========" << endl;
    cout << "按任意键退出..." << endl;
    cin.get();

    return 0;
}