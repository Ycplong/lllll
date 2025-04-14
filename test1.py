import os
import shutil


class YourClass:
    def __init__(self, machine_path):
        self.machine_path = machine_path

    def data2lake(self, local_path, filename, tif):
        """
        数据入湖
        :param local_path: 本地路径
        :param filename: 文件名称
        :param tif: True/False
        :return: 1表示成功，0表示失败
        """
        try:
            # 规范化路径，处理可能的路径分隔符问题
            local_path = os.path.normpath(local_path)
            # 检查本地文件是否存在
            print(f"共享存储路径地址{self.machine_path}")

            if not os.path.exists(local_path):
                print(f"本地路径不存在: {local_path}")
                return 0

            try:
                if tif:
                    # 若 local_path 是文件，直接移动到共享存储
                    if os.path.isfile(local_path):
                        shutil.move(local_path, os.path.join(self.machine_path, filename))
                        print(f"tiff文件:{filename}入湖成功")
                        return 1
                    else:
                        print(f"本地路径 {local_path} 不是一个文件")
                        return 0
                else:
                    local_file_path = os.path.join(local_path, filename)
                    # 若 local_file_path 是文件，直接移动到共享存储
                    if os.path.isfile(local_file_path):
                        shutil.move(local_file_path, os.path.join(self.machine_path, filename))
                        print(f"klarf文件:{filename}入湖成功")
                        return 1
                    else:
                        print(f"本地文件 {local_file_path} 不存在")
                        return 0

            except Exception as operation_error:
                print(f"文件传输失败: {str(operation_error)}")
                return 0

        except Exception as e:
            print(f"数据入湖过程中发生错误: {str(e)}")
            return 0

if __name__ == "__main__":
    shared_storage_path = "/shared-storage"
    obj = YourClass(shared_storage_path)
    result = obj.data2lake("/local/path", "test.txt", False)
    print(f"入湖结果: {result}")
