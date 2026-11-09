from langgraph.graph import StateGraph


# todo 一、最开始的时候使用函数式节点做graph流程
from zzk.import_process.state import ImportGraphState

def a():
    pass

def b():
    pass
builder = StateGraph(state_schema=ImportGraphState)

builder.add_node(a)
builder.add_edge(a, b)

graph = builder.compile()
result = graph.invoke({})
# 后期这个函数谁调用的,不是我们调的函数节点，我们只是添加了一下函数节点，但是最终函数代码执行了
# 函数肯定有人帮我们调了，否则代码不可能走，是graph帮我们调用的，函数调用的时候谁调用谁负责传参、
#函数后期会被调用执行函数当中的代码


# todo 二、 函数节点的调用和类实例化对象的调用，其实本质一样都是执行函数当中的代码，类实例化对象执行的是call的代码
class A:
    def __call__(self):
        pass


#如果我们添加节点添加的不是函数，而是一个实例化对象会发生啥事呢？
#后期graph也要调用这个对象，它会把对象当函数去调用,只不过把对象当函数去调用的时候，自动调用__call__方法
builder.add_node(A())






# todo 三、把函数节点完全变成类式节点

#到此为止后期我们写节点就可以写成类
#假设后期有多个节点，每个节点写一个类 类里面一定要写__call__方法
#假设我现在需要2哥节点，每个节点都是一个类
class B:
    def __call__(self):
        pass

class C:
    def __call__(self):
        pass

builder.add_node(B())
builder.add_node(C())




# todo 四、把call方法提到父类当中
# 每个节点都写了一个 __call__方法，我就在想能不能把call方法提到父类当中
class Base:
    def __call__(self):
        pass

class B(Base):
    pass

class C(Base):
    pass

builder.add_node(B())
builder.add_node(C())

#这样确实可以省略很多call方法，但是新的问题是，每个节点的功能是不一样的，所以父类的call方法没办法写多个节点不同的功能



# todo 五、使用抽象类和抽象方法，让子类实现抽象方法，解决call当中执行不同的节点功能
#父类变成抽象类，抽象类必须要有一个抽象方法，而且所有的子类必须实现父类的抽象方法
#抽象类其实本质是定义了一套规则（类似java的接口）

#抽象类必须要有一个抽象方法，而且所有的子类必须实现父类的抽象方法
#抽象类不能实例化


from abc import ABC, abstractmethod
class Base(ABC):
    def __call__(self):
        self.process()

    @abstractmethod
    def process(self):
        pass

class B(Base):
    def process(self):
        # 这里写节点逻辑
        pass


class C(Base):
    def process(self):
        # 这里写节点逻辑
        pass































