# 程序：代码的集合 一般就是文件 程序是死的 就是硬盘上的一个文件，程序是静态的。
# 进程：就是程序的一次过程 程序运行起来就变成进程。进程是活的，会占用资源 cpu 内存等资源。 进程是动态的
# 线程：线程依赖进程，每个进程至少要有一个线程（主线程），线程是执行代码的最小单位。线程也有自己的资源，只是自己的资源很小，大部分共用进程的资源。
from langchain.chat_models import init_chat_model

#进程是线程的爹 进程的资源占用比线程要大很多


# 多进程和多线程
# 无论是多进程还是多线程其实最基本的作用就是解决阻塞，只是在某些方面擅长的不一样罢了，cpu密集型任务和io密集型任务



# import time
# import threading
# def fn1():
#     print(threading.current_thread().name) #可以打印子线程的名字
#     print("我爱你杨幂")
#     time.sleep(2)
#     print("我爱你赵丽颖")
#
# def fn2():
#     print(threading.current_thread().name)
#     print("我爱你迪丽热巴")
#     time.sleep(2)
#     print("我爱你马尔扎哈")
#
#
# if __name__ == '__main__':
#     # print(threading.current_thread().name) #可以打印主线程的名字
#     # start = time.time()
#     # fn1()
#     # fn2()
#     # end = time.time()
#     # print(end - start)
#     # 出现阻塞 串行
#
#     # 使用多线程
#     start = time.time()
#     t1 = threading.Thread(target=fn1,name="thread01",args=())
#     print(threading.current_thread().name)
#     t2 = threading.Thread(target=fn2,name="thread02",args=())
#     t1.start()
#     t2.start()
#     t1.join() #让主线程等待子线程执行结束
#     t2.join()
#     end = time.time()
#     print(end - start)









# import time
# import multiprocessing
# def fn1():
#     print(multiprocessing.current_process().name)
#     print("我爱你杨幂")
#     time.sleep(2)
#     print("我爱你赵丽颖")
#
# def fn2():
#     print(multiprocessing.current_process().name)
#     print("我爱你迪丽热巴")
#     time.sleep(2)
#     print("我爱你马尔扎哈")
#
#
# class MyProcess(multiprocessing.Process):
#     def __init__(self,target,name,args=()):
#         super().__init__()
#         self.target = target
#         self.name = name
#         self.args = args
#
#     def run(self):
#         self.target(*self.args)
#
# if __name__ == '__main__':
#     # 串行
#     # start = time.time()
#     # fn1()
#     # fn2()
#     # end = time.time()
#     # print(end - start)
#
#     print(multiprocessing.current_process().name)
#     # 多进程执行
#     start = time.time()
#     # p1 = multiprocessing.Process(target=fn1,name="pro01",args=())
#     # p2 = multiprocessing.Process(target=fn2,name="pro02",args=())
#
#     # 使用进程类
#     p1 = MyProcess(target=fn1, name="pro01", args=())
#     p2 = MyProcess(target=fn2, name="pro02", args=())
#     p1.start()
#     p2.start()
#     p1.join()
#     p2.join()
#     end = time.time()
#     print(end - start)





#线程锁的使用

# import time
# from concurrent.futures import ThreadPoolExecutor
# import threading
#
#
# count = 0
#
# # 创建锁
# lock = threading.Lock()
#
# def count_num(n):
#     global count
#     for i in range(n):
#         # lock.acquire() #上锁 其余线程执行到这里全部强制等待
#         num = count
#         time.sleep(0)
#         num += 1
#         count = num
#         # lock.release() #解锁，数据操作完成安全解锁，让其它线程有机会操作
#         # count += 1
#
#
#
#
# if __name__ == '__main__':
#     with ThreadPoolExecutor(max_workers=2) as executor:
#         executor.map(count_num, [1000,1000])
#
#     print(count)


# 线程是不安全的，此时我们就得使用线程锁（互斥锁）来解决这个问题
# 以后只要碰到是多线程在操作全局变量，无脑加锁


# 总结多进程 ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** *
# io密集型任务可以选择多线程
# cpu密集型任务必须选择多进程
#
# io密集型
# io阻塞比较多
# 假设选择多进程，就会出现cpu一直处于等待状态，虽然多个核心可以实现并行，
# 但是资源浪费厉害，性能消耗（创建进程和切换进程）也厉害，多线程虽然不能并行，但是它也属于高并发
# 因为GIL锁的释放条件明确说明只要io阻塞立即释放，所以多线程在执行io密集型任务的时候释放锁速度也很快
# 线程在等待的时候也有状态切换，线程也需要创建，但是比起进程来说就是小巫见大巫



# cpu密集型
# cpu的计算量比较大
# 假设选择多线程
# GIL锁的存在导致同一时刻只能一个线程执行计算代码，而且不存在io阻塞
# 每个线程在执行的时候都得完整执行完100条件字节码指令才会强制被交出GIL锁，在此期间剩余的所有线程都处于排队等待状态
# 后面拿到锁再去执行。来回不管怎么切换锁，都是只有一个线程在执行代码也就是说只有一个核心在进行cpu的计算，其余得所有
# cpu核心根本没用到。因此计算的时候效率极低。
#
#
# 多进程处理cpu密集型任务，虽然每个进程也有GIL锁，但是此时对于每个进程来说GIL锁相当于摆设，因为每个进程里面只有一个线程
# 不存在线程之间的锁切换。而且最主要的是，多进程实现的是真正的并行，每个进程都可以去参与计算，最大限度使用cpu的核心资源
# 因此计算的效率是最高的
#
# 注意：
# IO
# 密集用多进程 → 「能跑，但血亏」；  资源开销很大
# 效率都被资源开销浪费了
# 计算密集用多线程 → 「能跑，但白瞎」   效率最低 速度还不如单进程单线程
#
# io密集型
# 使用多线程
# cpu密集型使用多进程


