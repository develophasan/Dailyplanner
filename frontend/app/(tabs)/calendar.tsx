import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Calendar } from 'react-native-calendars';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';

const BACKEND_URL = Constants.expoConfig?.extra?.backendUrl || Constants.expoConfig?.hostUri 
  ? `http://${Constants.expoConfig.hostUri.split(':')[0]}:8001` 
  : 'http://localhost:8001';

interface Plan {
  id: string;
  date: string;
  title?: string;
  ageBand: string;
  planJson: any;
}

interface MarkedDates {
  [key: string]: {
    marked: boolean;
    dotColor: string;
    selectedColor?: string;
  };
}

export default function CalendarScreen() {
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState('');
  const [markedDates, setMarkedDates] = useState<MarkedDates>({});

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const token = await AsyncStorage.getItem('authToken');
      
      if (!token) {
        Alert.alert('Hata', 'Giriş yapmanız gerekiyor');
        return;
      }

      // Get current month's first and last day
      const now = new Date();
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
      const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      
      const fromDate = firstDay.toISOString().split('T')[0];
      const toDate = lastDay.toISOString().split('T')[0];

      const response = await fetch(
        `${BACKEND_URL}/api/plans/daily?from_date=${fromDate}&to_date=${toDate}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setPlans(data);
        
        // Create marked dates for calendar
        const marked: MarkedDates = {};
        data.forEach((plan: Plan) => {
          marked[plan.date] = {
            marked: true,
            dotColor: '#3498db',
          };
        });
        
        setMarkedDates(marked);
      } else {
        console.error('Failed to fetch plans');
      }
    } catch (error) {
      console.error('Error fetching plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDayPress = (day: any) => {
    setSelectedDate(day.dateString);
    
    // Find plan for selected date
    const planForDate = plans.find(plan => plan.date === day.dateString);
    if (planForDate) {
      router.push(`/plan/${planForDate.id}?type=daily`);
    } else {
      Alert.alert(
        'Plan Oluştur', 
        `${day.dateString} için plan oluşturmak ister misiniz?`,
        [
          { text: 'İptal', style: 'cancel' },
          { 
            text: 'Oluştur', 
            onPress: () => router.push('/(tabs)/chat')
          }
        ]
      );
    }
  };

  const handleMonthChange = (month: any) => {
    // Fetch plans for new month
    const newDate = new Date(month.year, month.month - 1, 1);
    fetchPlansForMonth(newDate);
  };

  const fetchPlansForMonth = async (date: Date) => {
    try {
      const token = await AsyncStorage.getItem('authToken');
      if (!token) return;

      const firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
      const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
      
      const fromDate = firstDay.toISOString().split('T')[0];
      const toDate = lastDay.toISOString().split('T')[0];

      const response = await fetch(
        `${BACKEND_URL}/api/plans/daily?from_date=${fromDate}&to_date=${toDate}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setPlans(data);
        
        // Update marked dates
        const marked: MarkedDates = {};
        data.forEach((plan: Plan) => {
          marked[plan.date] = {
            marked: true,
            dotColor: '#3498db',
          };
        });
        
        setMarkedDates(marked);
      }
    } catch (error) {
      console.error('Error fetching plans for month:', error);
    }
  };

  const renderPlansList = () => {
    const selectedDatePlans = plans.filter(plan => plan.date === selectedDate);
    
    if (selectedDate && selectedDatePlans.length === 0) {
      return (
        <View style={styles.noPlanContainer}>
          <Text style={styles.noPlanText}>
            {selectedDate} için henüz plan oluşturulmamış.
          </Text>
          <TouchableOpacity 
            style={styles.createButton}
            onPress={() => router.push('/(tabs)/chat')}
          >
            <Text style={styles.createButtonText}>Plan Oluştur</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return selectedDatePlans.map((plan) => (
      <TouchableOpacity
        key={plan.id}
        style={styles.planItem}
        onPress={() => router.push(`/plan-detail?id=${plan.id}&type=daily`)}
      >
        <Text style={styles.planTitle}>{plan.title || 'Günlük Plan'}</Text>
        <Text style={styles.planDate}>{plan.date}</Text>
        <Text style={styles.planAge}>Yaş Grubu: {plan.ageBand}</Text>
      </TouchableOpacity>
    ));
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3498db" />
        <Text style={styles.loadingText}>Planlar yükleniyor...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>📅 Takvim</Text>
        <Text style={styles.subtitle}>
          Planlarınızı görüntülemek için tarihe tıklayın
        </Text>
      </View>

      <Calendar
        onDayPress={handleDayPress}
        onMonthChange={handleMonthChange}
        monthFormat={'yyyy MMMM'}
        hideExtraDays={true}
        disableMonthChange={false}
        firstDay={1}
        hideDayNames={false}
        showWeekNumbers={false}
        onPressArrowLeft={(subtractMonth) => subtractMonth()}
        onPressArrowRight={(addMonth) => addMonth()}
        markingType={'dot'}
        markedDates={{
          ...markedDates,
          [selectedDate]: {
            ...markedDates[selectedDate],
            selected: true,
            selectedColor: '#2980b9',
          },
        }}
        theme={{
          backgroundColor: '#ffffff',
          calendarBackground: '#ffffff',
          textSectionTitleColor: '#b6c1cd',
          selectedDayBackgroundColor: '#2980b9',
          selectedDayTextColor: '#ffffff',
          todayTextColor: '#3498db',
          dayTextColor: '#2d4150',
          textDisabledColor: '#d9e1e8',
          dotColor: '#3498db',
          selectedDotColor: '#ffffff',
          arrowColor: '#3498db',
          disabledArrowColor: '#d9e1e8',
          monthTextColor: '#2d4150',
          indicatorColor: '#3498db',
        }}
      />

      {selectedDate && (
        <View style={styles.selectedDateContainer}>
          <Text style={styles.selectedDateTitle}>
            📋 {selectedDate} Planları
          </Text>
          {renderPlansList()}
        </View>
      )}

      <View style={styles.legend}>
        <View style={styles.legendItem}>
          <View style={styles.dot} />
          <Text style={styles.legendText}>Plan var</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  loadingContainer: {
    flex: 1, 
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  header: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#7f8c8d',
  },
  selectedDateContainer: {
    margin: 20,
    padding: 15,
    backgroundColor: '#fff',
    borderRadius: 10,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  selectedDateTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 10,
  },
  planItem: {
    padding: 15,
    backgroundColor: '#ecf0f1',
    borderRadius: 8,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#3498db',
  },
  planTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 5,
  },
  planDate: {
    fontSize: 14,
    color: '#7f8c8d',
    marginBottom: 2,
  },
  planAge: {
    fontSize: 14,
    color: '#95a5a6',
  },
  noPlanContainer: {
    padding: 20,
    alignItems: 'center',
  },
  noPlanText: {
    fontSize: 16,
    color: '#7f8c8d',
    textAlign: 'center',
    marginBottom: 15,
  },
  createButton: {
    backgroundColor: '#3498db',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
  },
  legend: {
    margin: 20,
    padding: 15,
    backgroundColor: '#fff',
    borderRadius: 10,
    elevation: 1,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#3498db',
    marginRight: 10,
  },
  legendText: {
    fontSize: 14,
    color: '#2c3e50',
  },
});