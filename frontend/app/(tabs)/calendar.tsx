import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Calendar } from 'react-native-calendars';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

interface Plan {
  id: string;
  date: string;
  title: string;
  ageBand: string;
}

interface MarkedDates {
  [key: string]: {
    marked: boolean;
    dotColor: string;
    plans: Plan[];
  };
}

export default function CalendarTab() {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [markedDates, setMarkedDates] = useState<MarkedDates>({});
  const [selectedDatePlans, setSelectedDatePlans] = useState<Plan[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadMonthPlans();
  }, []);

  useEffect(() => {
    updateSelectedDatePlans();
  }, [selectedDate, markedDates]);

  const getAuthToken = async () => {
    return await AsyncStorage.getItem('authToken');
  };

  const loadMonthPlans = async () => {
    setIsLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) {
        router.replace('/auth/login');
        return;
      }

      // Get current month's first and last day
      const now = new Date();
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
      const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);

      const response = await fetch(`${BACKEND_URL}/api/plans/daily?from_date=${firstDay.toISOString().split('T')[0]}&to_date=${lastDay.toISOString().split('T')[0]}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          router.replace('/auth/login');
          return;
        }
        throw new Error('Planlar yüklenemedi');
      }

      const plans: Plan[] = await response.json();
      
      // Group plans by date
      const dateMap: MarkedDates = {};
      plans.forEach(plan => {
        const dateKey = plan.date.split('T')[0];
        if (!dateMap[dateKey]) {
          dateMap[dateKey] = {
            marked: true,
            dotColor: '#3498db',
            plans: [],
          };
        }
        dateMap[dateKey].plans.push(plan);
      });

      setMarkedDates(dateMap);
    } catch (error) {
      console.error('Load calendar plans error:', error);
      Alert.alert('Hata', 'Takvim planları yüklenirken hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const updateSelectedDatePlans = () => {
    const plans = markedDates[selectedDate]?.plans || [];
    setSelectedDatePlans(plans);
  };

  const formatAgeBand = (ageBand: string) => {
    const ageMap: { [key: string]: string } = {
      '36_48': '36-48 Ay',
      '48_60': '48-60 Ay',
      '60_72': '60-72 Ay',
    };
    return ageMap[ageBand] || ageBand;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('tr-TR', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const viewPlan = (planId: string) => {
    router.push(`/plan/${planId}`);
  };

  const createPlanForDate = () => {
    // Navigate to chat with pre-filled date context
    router.push('/(tabs)/chat');
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Takvim</Text>
        <TouchableOpacity onPress={loadMonthPlans} style={styles.refreshButton}>
          <Ionicons name="refresh-outline" size={24} color="#3498db" />
        </TouchableOpacity>
      </View>

      <View style={styles.calendarContainer}>
        <Calendar
          current={selectedDate}
          onDayPress={(day) => setSelectedDate(day.dateString)}
          markedDates={{
            ...markedDates,
            [selectedDate]: {
              ...markedDates[selectedDate],
              selected: true,
              selectedColor: '#3498db',
            },
          }}
          theme={{
            backgroundColor: '#ffffff',
            calendarBackground: '#ffffff',
            textSectionTitleColor: '#2c3e50',
            selectedDayBackgroundColor: '#3498db',
            selectedDayTextColor: '#ffffff',
            todayTextColor: '#3498db',
            dayTextColor: '#2c3e50',
            textDisabledColor: '#bdc3c7',
            dotColor: '#3498db',
            selectedDotColor: '#ffffff',
            arrowColor: '#3498db',
            monthTextColor: '#2c3e50',
            indicatorColor: '#3498db',
            textDayFontWeight: '500',
            textMonthFontWeight: 'bold',
            textDayHeaderFontWeight: '500',
            textDayFontSize: 16,
            textMonthFontSize: 18,
            textDayHeaderFontSize: 14,
          }}
          firstDay={1}
          hideExtraDays={true}
          showWeekNumbers={false}
        />
      </View>

      <View style={styles.selectedDateContainer}>
        <Text style={styles.selectedDateTitle}>{formatDate(selectedDate)}</Text>
        
        {selectedDatePlans.length > 0 ? (
          <ScrollView style={styles.plansContainer}>
            {selectedDatePlans.map((plan) => (
              <TouchableOpacity
                key={plan.id}
                style={styles.planCard}
                onPress={() => viewPlan(plan.id)}
              >
                <View style={styles.planHeader}>
                  <Text style={styles.planTitle}>{plan.title}</Text>
                  <Text style={styles.planAgeBand}>{formatAgeBand(plan.ageBand)}</Text>
                </View>
                
                <View style={styles.planFooter}>
                  <TouchableOpacity style={styles.viewButton}>
                    <Ionicons name="eye-outline" size={16} color="#3498db" />
                    <Text style={styles.viewButtonText}>Görüntüle</Text>
                  </TouchableOpacity>
                  <Ionicons name="chevron-forward-outline" size={16} color="#bdc3c7" />
                </View>
              </TouchableOpacity>
            ))}
          </ScrollView>
        ) : (
          <View style={styles.emptyContainer}>
            <Ionicons name="calendar-outline" size={48} color="#bdc3c7" />
            <Text style={styles.emptyTitle}>Bu tarih için plan bulunamadı</Text>
            <Text style={styles.emptySubtitle}>Bu tarih için yeni bir plan oluşturmak ister misiniz?</Text>
            
            <TouchableOpacity style={styles.createButton} onPress={createPlanForDate}>
              <Ionicons name="add" size={20} color="white" />
              <Text style={styles.createButtonText}>Plan Oluştur</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  refreshButton: {
    padding: 4,
  },
  calendarContainer: {
    backgroundColor: 'white',
    marginBottom: 8,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  selectedDateContainer: {
    flex: 1,
    backgroundColor: 'white',
    paddingTop: 16,
  },
  selectedDateTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    textAlign: 'center',
    marginBottom: 16,
  },
  plansContainer: {
    flex: 1,
    paddingHorizontal: 16,
  },
  planCard: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e1e8ed',
  },
  planHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  planTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    flex: 1,
    marginRight: 8,
  },
  planAgeBand: {
    backgroundColor: '#3498db',
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
  },
  planFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  viewButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  viewButtonText: {
    fontSize: 14,
    color: '#3498db',
    marginLeft: 4,
    fontWeight: '500',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginTop: 16,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#7f8c8d',
    marginTop: 8,
    textAlign: 'center',
    lineHeight: 20,
  },
  createButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#3498db',
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 20,
    marginTop: 16,
  },
  createButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
});