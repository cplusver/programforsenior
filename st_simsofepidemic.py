import streamlit as st
import networkx as nx

from pylab import *
mpl.rcParams['font.sans-serif'] = ['SimHei']
# 页面标题
st.title("疫情传播模拟")  # 在这里修改你的标题，例如：疫情传播模拟

# 添加文本
st.text("在设置好左边的参数后点击下方按钮")  # 这里写介绍文本
start_button = st.button("开始模拟")  # 这个是按钮

# 创建一个空的图表容器
chart_container = st.empty()

# 添加侧边栏
st.sidebar.header("参数调整")
st.sidebar.write("在以下输入框内调整你的参数：")
TT = int(st.sidebar.text_input("模拟时间步长", 100))
rou1 = float(st.sidebar.text_input("接种疫苗对感染的防护率", 0.4))
beta_unvaccinated = float(st.sidebar.text_input("未接种疫苗者的传染率", 0.3))
sigma = float(st.sidebar.text_input("潜伏期转化为感染者概率", 0.1))
gamma = float(st.sidebar.text_input("个体康复率", 0.05))
g = float(st.sidebar.text_input("政策强度(0~1)", 0))
prob_vaccination = float(st.sidebar.text_input("未打疫苗易感者自发变成打疫苗易感者的概率", 0.1))
rou2 = float(st.sidebar.text_input("打疫苗对传染病的防护效率", 0.8))
normal_death_rate = float(st.sidebar.text_input("正常死亡率", 0.02))
N = int(st.sidebar.text_input("总人口数", 200))
i0 = float(st.sidebar.text_input("初始感染密度", 0.01))
E0 = int(st.sidebar.text_input("初始潜伏期人数", 1))
R0 = int(st.sidebar.text_input("初始康复人数", 0))
I0 = int(N * i0)  # 将浮点数转换为整数
S0 = N - I0 - E0 - R0  # 初始易感染人数
beta_vaccinated = beta_unvaccinated * (1-rou1)
low_death_rate = normal_death_rate * (1-rou2)   # 较低死亡率（之前成为过打疫苗易感者）

# 创建小世界网络
num_nodes = N
avg_degree = 8
rewiring_prob = 0.2
G = nx.watts_strogatz_graph(num_nodes, avg_degree, rewiring_prob)

# 创建无标度网络
num_nodes = N
m = 5  # 每个新节点的连边数
G = nx.barabasi_albert_graph(num_nodes, m)

# 创建均匀网络
num_nodes = N  # 总节点数
p = 0.1  # 边的概率，可以调整这个值来控制网络的稀疏程度
G = nx.erdos_renyi_graph(num_nodes, p)

# 初始化节点状态
initial_infected = np.random.choice(G.nodes(), size=I0, replace=False)
initial_exposed = np.random.choice(list(set(G.nodes()) - set(initial_infected)), size=E0, replace=False)

# 假设有一部分人已经接种了疫苗
vaccinated_fraction = 0.4  # 接种疫苗的比例
num_vaccinated = int(N * vaccinated_fraction)

# 随机选择一些节点成为打疫苗的，数目与接种疫苗的人数一致
vaccinated_nodes = np.random.choice(G.nodes(), size=num_vaccinated, replace=False)

# 设置初始状态
for node in G.nodes():
    if node in initial_infected:
        G.nodes[node]['status'] = 'I'  # 感染者
    elif node in initial_exposed:
        G.nodes[node]['status'] = 'E'  # 潜伏者
    elif node in vaccinated_nodes:
        G.nodes[node]['status'] = 'S_vaccinated'  # 打疫苗易感者
    else:
        G.nodes[node]['status'] = 'S_unvaccinated'  # 未打疫苗易感者

# 记录每种状态的数量随时间变化
num_S_vaccinated = [num_vaccinated]
num_S_unvaccinated = [N - num_vaccinated]
num_E = [E0]
num_I = [I0]
num_R = [R0]
num_D = [0]  # 初始没有死亡者


# 定义传播函数
def spread_disease(G, beta_vaccinated, beta_unvaccinated, sigma, gamma, prob_vaccination, normal_death_rate,
                   low_death_rate):
    new_infected = []
    new_exposed = []  # 新增潜伏者列表
    new_recovered = []  # 新增恢复者列表
    new_dead = []  # 新增死亡者列表
    for node in G.nodes():
        if G.nodes[node]['status'] == 'I':
            neighbors = list(G.neighbors(node))
            for neighbor in neighbors:
                if G.nodes[neighbor]['status'] == 'S_vaccinated' and np.random.rand() < beta_vaccinated * (1 - g):
                    new_exposed.append(neighbor)  # 易感者变成潜伏者
                elif G.nodes[neighbor]['status'] == 'S_unvaccinated' and np.random.rand() < beta_unvaccinated * (1 - g):
                    new_exposed.append(neighbor)  # 易感者变成潜伏者
            if np.random.rand() < gamma:  # 判断是否康复
                new_recovered.append(node)
                if G.nodes[node]['status'] == 'I' and G.nodes[node].get('vaccinated', True):
                    if np.random.rand() < low_death_rate:  # 如果之前成为过打疫苗易感者，以较低的概率成为死亡者
                        new_dead.append(node)
                else:
                    if np.random.rand() < normal_death_rate:  # 否则以正常概率成为死亡者
                        new_dead.append(node)
                    else:
                        new_recovered.append(node)
        elif G.nodes[node]['status'] == 'E':
            neighbors = list(G.neighbors(node))
            for neighbor in neighbors:
                if G.nodes[neighbor]['status'] == 'S_vaccinated' and np.random.rand() < beta_vaccinated * (1 - g):
                    new_infected.append(neighbor)  # 潜伏者感染易感者
                elif G.nodes[neighbor]['status'] == 'S_unvaccinated' and np.random.rand() < beta_unvaccinated * (1 - g):
                    new_infected.append(neighbor)  # 潜伏者感染易感者
            if np.random.rand() < sigma:  # 潜伏者自身转为感染者的概率
                new_infected.append(node)
    for node in new_exposed:  # 设置潜伏者状态
        G.nodes[node]['status'] = 'E'
    for node in new_infected:
        G.nodes[node]['status'] = 'I'
    for node in new_recovered:  # 设置恢复者状态
        G.nodes[node]['status'] = 'R'
    for node in new_dead:  # 设置死亡者状态
        G.nodes[node]['status'] = 'D'

    # 添加标记以记录之前成为过打疫苗易感者的感染者
    for node in G.nodes():
        if G.nodes[node]['status'] == 'I' and G.nodes[node]['status'] != 'R':
            G.nodes[node]['vaccinated'] = True


# 模拟传播过程
num_steps = TT

fig, ax = plt.subplots(figsize=(10, 8))


def update(frame):
    ax.clear()
    ax.set_title(f'Time Step: {frame}')

    spread_disease(G, beta_vaccinated, beta_unvaccinated, sigma, gamma, prob_vaccination, normal_death_rate,
                   low_death_rate)

    # 绘制网络状态
    node_colors = []
    for node in G.nodes():
        if G.nodes[node]['status'] == 'I':
            node_colors.append('red')
        elif G.nodes[node]['status'] == 'E':
            node_colors.append('orange')
        elif G.nodes[node]['status'] == 'R':
            node_colors.append('green')  # 恢复者以绿色表示
        elif G.nodes[node]['status'] == 'S_vaccinated':
            node_colors.append('blue')  # 打疫苗易感者以蓝色表示
        elif G.nodes[node]['status'] == 'D':
            node_colors.append('black')  # 死亡者以黑色表示
        else:
            node_colors.append('purple')  # 未打疫苗易感者以紫色表示

    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, ax=ax, pos=pos, node_color=node_colors, with_labels=False, node_size=50)

    # 更新每种状态的数量
    num_S_vaccinated.append(len([node for node in G.nodes() if G.nodes[node]['status'] == 'S_vaccinated']))
    num_S_unvaccinated.append(len([node for node in G.nodes() if G.nodes[node]['status'] == 'S_unvaccinated']))
    num_E.append(len([node for node in G.nodes() if G.nodes[node]['status'] == 'E']))
    num_I.append(len([node for node in G.nodes() if G.nodes[node]['status'] == 'I']))
    num_R.append(len([node for node in G.nodes() if G.nodes[node]['status'] == 'R']))
    num_D.append(len([node for node in G.nodes() if G.nodes[node]['status'] == 'D']))

    # 添加图例

    legend_labels = {
        'S_vaccinated': '打疫苗易感者',
        'S_unvaccinated': '未打疫苗易感者',
        'E': '潜伏者',
        'I': '感染者',
        'R': '恢复者',
        'D': '死亡者'
    }
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w', label=legend_labels[status],
                                  markersize=10, markerfacecolor=color) for status, color in
                       zip(['S_vaccinated', 'S_unvaccinated', 'E', 'I', 'R', 'D'],
                           ['blue', 'purple', 'orange', 'red', 'green', 'black'])]
    ax.legend(handles=legend_elements, loc='upper right')
    return fig


chart_index = 0
if start_button:
    chart_index = 0
    while chart_index <= TT:
        fig = update(chart_index)
        chart_container.pyplot(fig)
        chart_index = chart_index + 1
        time.sleep(0.1)
if chart_index == TT + 1:
    st.success("模拟完成！")
