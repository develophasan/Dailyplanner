import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL || 'https://plan-tester-1.preview.emergentagent.com';

interface Plan {
  id: string;
  date?: string;
  month?: string;
  ageBand: string;
  title: string;
  createdAt: string;
  pdfUrl?: string;
}

export default function Plans() {
  const [activeTab, setActiveTab] = useState<'daily' | 'monthly'>('daily');
  const [dailyPlans, setDailyPlans] = useState<Plan[]>([]);
  const [monthlyPlans, setMonthlyPlans] = useState<Plan[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadPlans();
  }, [activeTab]);

  const getAuthToken = async () => {
    return await AsyncStorage.getItem('authToken');
  };

  const deletePlan = async (planId: string, planType: 'daily' | 'monthly') => {
    Alert.alert(
      'Planı Sil',
      'Bu planı silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.',
      [
        { text: 'İptal', style: 'cancel' },
        { 
          text: 'Sil', 
          style: 'destructive',
          onPress: async () => {
            try {
              const token = await getAuthToken();
              if (!token) return;

              const response = await fetch(`${BACKEND_URL}/api/plans/${planType}/${planId}`, {
                method: 'DELETE',
                headers: {
                  'Authorization': `Bearer ${token}`,
                },
              });

              if (response.ok) {
                Alert.alert('Başarılı', 'Plan silindi');
                loadPlans(); // Refresh plans
              } else {
                Alert.alert('Hata', 'Plan silinirken bir hata oluştu');
              }
            } catch (error) {
              console.error('Plan silme hatası:', error);
              Alert.alert('Hata', 'Bağlantı hatası');
            }
          }
        }
      ]
    );
  };

  const loadPlans = async () => {
    setIsLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) {
        router.replace('/auth/login');
        return;
      }

      const endpoint = activeTab === 'daily' ? '/api/plans/daily' : '/api/plans/monthly';
      const response = await fetch(`${BACKEND_URL}${endpoint}`, {
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

      const plans = await response.json();
      
      if (activeTab === 'daily') {
        setDailyPlans(plans);
      } else {
        setMonthlyPlans(plans);
      }
    } catch (error) {
      console.error('Load plans error:', error);
      Alert.alert('Hata', 'Planlar yüklenirken hata oluştu.');
    } finally {
      setIsLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadPlans();
    setRefreshing(false);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('tr-TR');
  };

  const formatAgeBand = (ageBand: string) => {
    const ageMap: { [key: string]: string } = {
      '36_48': '36-48 Ay',
      '48_60': '48-60 Ay',
      '60_72': '60-72 Ay',
    };
    return ageMap[ageBand] || ageBand;
  };

  const viewPlan = (planId: string) => {
    router.push(`/plan/${planId}?type=${activeTab}`);
  };

  const createNewPlan = () => {
    router.push('/(tabs)/chat');
  };

  const currentPlans = activeTab === 'daily' ? dailyPlans : monthlyPlans;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Planlarım</Text>
        <TouchableOpacity onPress={createNewPlan} style={styles.addButton}>
          <Ionicons name="add" size={24} color="white" />
        </TouchableOpacity>
      </View>

      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'daily' && styles.activeTab]}
          onPress={() => setActiveTab('daily')}
        >
          <Text style={[styles.tabText, activeTab === 'daily' && styles.activeTabText]}>
            Günlük Planlar
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'monthly' && styles.activeTab]}
          onPress={() => setActiveTab('monthly')}
        >
          <Text style={[styles.tabText, activeTab === 'monthly' && styles.activeTabText]}>
            Aylık Planlar
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.plansContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {currentPlans.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="document-outline" size={64} color="#bdc3c7" />
            <Text style={styles.emptyTitle}>
              {activeTab === 'daily' ? 'Günlük plan' : 'Aylık plan'} bulunamadı
            </Text>
            <Text style={styles.emptySubtitle}>
              Yeni bir plan oluşturmak için AI asistanı kullanın
            </Text>
            <TouchableOpacity style={styles.createButton} onPress={createNewPlan}>
              <Text style={styles.createButtonText}>Plan Oluştur</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.plansList}>
            {currentPlans.map((plan) => (
              <TouchableOpacity
                key={plan.id}
                style={styles.planCard}
                onPress={() => viewPlan(plan.id)}
              >
                <View style={styles.planHeader}>
                  <Text style={styles.planTitle}>{plan.title}</Text>
                  <Text style={styles.planAgeBand}>{formatAgeBand(plan.ageBand)}</Text>
                </View>
                
                <View style={styles.planInfo}>
                  <View style={styles.planInfoItem}>
                    <Ionicons name="calendar-outline" size={16} color="#7f8c8d" />
                    <Text style={styles.planInfoText}>
                      {plan.date ? formatDate(plan.date) : plan.month}
                    </Text>
                  </View>
                  
                  <View style={styles.planInfoItem}>
                    <Ionicons name="time-outline" size={16} color="#7f8c8d" />
                    <Text style={styles.planInfoText}>
                      {formatDate(plan.createdAt)}
                    </Text>
                  </View>
                </View>

                <View style={styles.planActions}>
                  <TouchableOpacity style={styles.actionButton}>
                    <Ionicons name="eye-outline" size={20} color="#3498db" />
                    <Text style={styles.actionButtonText}>Görüntüle</Text>
                  </TouchableOpacity>
                  
                  {plan.pdfUrl && (
                    <TouchableOpacity style={styles.actionButton}>
                      <Ionicons name="download-outline" size={20} color="#27ae60" />
                      <Text style={styles.actionButtonText}>PDF</Text>
                    </TouchableOpacity>
                  )}
                  
                  <TouchableOpacity 
                    style={[styles.actionButton, styles.deleteButton]}
                    onPress={() => deletePlan(plan.id, activeTab)}
                  >
                    <Ionicons name="trash-outline" size={20} color="#e74c3c" />
                    <Text style={[styles.actionButtonText, styles.deleteText]}>Sil</Text>
                  </TouchableOpacity>
                </View>
                
                <View style={styles.planCardFooter}>
                  <Ionicons name="chevron-forward-outline" size={20} color="#bdc3c7" />
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </ScrollView>
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
  addButton: {
    backgroundColor: '#3498db',
    borderRadius: 20,
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  activeTab: {
    borderBottomColor: '#3498db',
  },
  tabText: {
    fontSize: 16,
    color: '#7f8c8d',
    fontWeight: '500',
  },
  activeTabText: {
    color: '#3498db',
    fontWeight: 'bold',
  },
  plansContainer: {
    flex: 1,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginTop: 16,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 16,
    color: '#7f8c8d',
    marginTop: 8,
    textAlign: 'center',
  },
  createButton: {
    backgroundColor: '#3498db',
    borderRadius: 8,
    paddingVertical: 12, 
    paddingHorizontal: 24,
    marginTop: 24,
  },
  createButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  plansList: {
    padding: 16,
  },
  planCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  planHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  planTitle: {
    fontSize: 18,
    fontWeight: 'bold',
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
    borderRadius: 12,
  },
  planInfo: {
    marginBottom: 16,
  },
  planInfoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  planInfoText: {
    fontSize: 14,
    color: '#7f8c8d',
    marginLeft: 8,
  },
  planActions: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
  },
  actionButtonText: {
    fontSize: 14,
    color: '#3498db',
    marginLeft: 4,
    fontWeight: '500',
  },
  deleteButton: {
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  deleteText: {
    color: '#e74c3c',
  },
  planCardFooter: {
    alignItems: 'flex-end',
  },
});