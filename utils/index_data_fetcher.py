"""
指数数据获取器
从 cn-lj.dat.gz 获取主要指数的量价数据
"""

import gzip
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path


class IndexDataFetcher:
    """指数数据获取器 - 获取上证指数、深证成指、创业板指、科创50的量价数据"""
    
    # 中国市场主要指数
    CN_INDICES = {
        '000001': '上证指数',
        '399001': '深证成指',
        '399006': '创业板指',
        '000688': '科创50'
    }
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.base_path = self._get_base_path()
        
    def _get_base_path(self):
        """获取基础路径"""
        if hasattr(os.sys, 'frozen'):
            return Path(os.sys.executable).parent
        else:
            return Path(__file__).parent.parent
    
    def _log(self, message):
        """输出日志"""
        if self.verbose:
            print(f"[IndexDataFetcher] {message}")
    
    def fetch_cn_indices_data(self, days=20):
        """
        获取中国市场主要指数的量价数据
        
        Args:
            days: 获取最近多少天的数据
            
        Returns:
            dict: 指数代码 -> {name, data: [(date, close, volume, change_pct), ...]}
        """
        try:
            # 找到 cn-lj.dat.gz 文件
            dat_file = self.base_path / 'cn-lj.dat.gz'
            
            if not dat_file.exists():
                self._log(f"指数数据文件不存在: {dat_file}")
                return {}
            
            # 解压并连接到 SQLite 数据库
            self._log(f"正在从 {dat_file} 加载指数数据...")
            
            with gzip.open(dat_file, 'rb') as f_in:
                # 创建临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
                    temp_db.write(f_in.read())
                    temp_db_path = temp_db.name
            
            try:
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()
                
                # 获取所有指数的量价数据
                indices_data = {}
                
                for index_code, index_name in self.CN_INDICES.items():
                    self._log(f"正在获取 {index_code} {index_name} 的数据...")
                    
                    # 查询最近N天的数据
                    cursor.execute("""
                        SELECT date, close, volume, 
                               CASE 
                                   WHEN LAG(close) OVER (ORDER BY date) IS NOT NULL 
                                   THEN ((close - LAG(close) OVER (ORDER BY date)) / LAG(close) OVER (ORDER BY date)) * 100
                                   ELSE 0 
                               END as change_pct
                        FROM volume_price_data
                        WHERE symbol = ? AND data_type = 'index'
                        ORDER BY date DESC
                        LIMIT ?
                    """, (index_code, days))
                    
                    rows = cursor.fetchall()
                    
                    if rows:
                        # 反转顺序（从旧到新）
                        rows = list(reversed(rows))
                        
                        indices_data[index_code] = {
                            'name': index_name,
                            'code': index_code,
                            'data': [
                                {
                                    'date': row[0],
                                    'close': float(row[1]) if row[1] else 0,
                                    'volume': float(row[2]) if row[2] else 0,
                                    'change_pct': float(row[3]) if row[3] else 0
                                }
                                for row in rows
                            ]
                        }
                        
                        self._log(f"  [OK] {index_name}: 获取到 {len(rows)} 条数据")
                    else:
                        self._log(f"  [FAIL] {index_name}: 未找到数据")
                
                conn.close()
                
                return indices_data
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_db_path)
                except:
                    pass
        
        except Exception as e:
            self._log(f"获取指数数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def format_indices_data_for_ai(self, indices_data):
        """
        格式化指数数据为AI提示词格式
        
        Args:
            indices_data: fetch_cn_indices_data() 返回的数据
            
        Returns:
            str: 格式化后的文本
        """
        if not indices_data:
            return "指数数据不可用"
        
        lines = []
        lines.append("【四、主要指数量价数据（最近20日）】")
        
        for index_code, index_info in indices_data.items():
            name = index_info['name']
            code = index_info['code']
            data = index_info['data']
            
            if not data:
                continue
            
            lines.append(f"\n* {name}（{code}）:")
            lines.append(f"  数据天数: {len(data)}天")
            
            # 最新价格和涨跌幅
            latest = data[-1]
            lines.append(f"  最新收盘: {latest['close']:.2f}")
            lines.append(f"  当日涨跌: {latest['change_pct']:+.2f}%")
            
            # 统计信息
            closes = [d['close'] for d in data]
            changes = [d['change_pct'] for d in data]
            volumes = [d['volume'] for d in data]
            
            # 价格区间
            min_price = min(closes)
            max_price = max(closes)
            price_range = ((max_price - min_price) / min_price) * 100
            lines.append(f"  价格区间: {min_price:.2f} ~ {max_price:.2f} (波动 {price_range:.2f}%)")
            
            # 平均涨跌幅
            avg_change = sum(changes) / len(changes) if changes else 0
            lines.append(f"  平均涨跌: {avg_change:+.2f}%/日")
            
            # 累计涨跌幅
            total_change = ((closes[-1] - closes[0]) / closes[0]) * 100 if closes[0] != 0 else 0
            lines.append(f"  累计涨跌: {total_change:+.2f}% ({len(data)}天)")
            
            # 成交量趋势
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
            recent_volume = volumes[-1] if volumes else 0
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            lines.append(f"  最近成交: {recent_volume/100000000:.2f}亿 (平均的 {volume_ratio:.2f}倍)")
            
            # 趋势判断
            if len(closes) >= 5:
                recent_5d_change = ((closes[-1] - closes[-5]) / closes[-5]) * 100 if closes[-5] != 0 else 0
                lines.append(f"  5日趋势: {recent_5d_change:+.2f}%")
                
                if recent_5d_change > 2:
                    trend = "上升趋势"
                elif recent_5d_change < -2:
                    trend = "下降趋势"
                else:
                    trend = "震荡整理"
                lines.append(f"  趋势状态: {trend}")
        
        return '\n'.join(lines)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("指数数据获取器测试")
    print("=" * 60)
    
    fetcher = IndexDataFetcher(verbose=True)
    
    print("\n正在获取中国市场主要指数数据...")
    indices_data = fetcher.fetch_cn_indices_data(days=20)
    
    print(f"\n获取到 {len(indices_data)} 个指数的数据")
    
    print("\n格式化后的AI提示词:")
    print("-" * 60)
    formatted = fetcher.format_indices_data_for_ai(indices_data)
    print(formatted)
    print("-" * 60)
    
    print("\n测试完成！")

