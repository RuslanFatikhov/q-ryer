# Временный скрипт для замены логики в order.py
import re

with open('app/models/order.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем и заменяем метод get_time_remaining
old_logic = r'''    def get_time_remaining\(self\):
        """Получение оставшегося времени до истечения заказа"""
        if self\.status in \['completed', 'cancelled'\]:
            return 0
            
        now = datetime\.utcnow\(\)
        
        if self\.status == 'pending':
            remaining = \(self\.expires_at - now\)\.total_seconds\(\)
        elif self\.status == 'active' and self\.pickup_time:
            delivery_deadline = self\.pickup_time \+ timedelta\(seconds=self\.timer_seconds \* 2\)
            remaining = \(delivery_deadline - now\)\.total_seconds\(\)
        else:
            remaining = 0
        
        return max\(0, int\(remaining\)\)'''

new_logic = '''    def get_time_remaining(self):
        """Получение оставшегося времени до истечения заказа"""
        if self.status in ['completed', 'cancelled']:
            return 0
            
        now = datetime.utcnow()
        
        if self.status == 'pending':
            # Время до истечения с момента создания
            remaining = (self.expires_at - now).total_seconds()
        elif self.status == 'active':
            if self.pickup_time:
                # Заказ забран - время до дедлайна доставки
                delivery_deadline = self.pickup_time + timedelta(seconds=self.timer_seconds * 2)
                remaining = (delivery_deadline - now).total_seconds()
            else:
                # Заказ принят но не забран - используем expires_at
                remaining = (self.expires_at - now).total_seconds()
        else:
            remaining = 0
        
        return max(0, int(remaining))'''

content = re.sub(old_logic, new_logic, content, flags=re.DOTALL)

with open('app/models/order.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Логика get_time_remaining исправлена")
