import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import Constants from 'expo-constants';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL || (typeof window !== 'undefined' ? window.location.origin : '');

interface Plan {
  id: string;
  date?: string;
  month?: string;
  ageBand: string;
  title: string;
  planJson: any;
  createdAt: string;
  pdfUrl?: string;
}

export default function PlansScreen() {
  const [activeTab, setActiveTab] = useState<'daily' | 'monthly'>('daily');
  const [plans, setPlans] = useState<Plan[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadPlans();
  }, [activeTab]);

  const getAuthToken = async () => {
    return await AsyncStorage.getItem('authToken');
  };

  const deletePlan = async (planId: string, planType: 'daily' | 'monthly') => {
    const confirmDelete = Platform.OS === 'web' 
      ? confirm('Bu planı silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.')
      : await new Promise((resolve) => {
          Alert.alert(
            'Planı Sil',
            'Bu planı silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.',
            [
              { text: 'İptal', onPress: () => resolve(false), style: 'cancel' },
              { text: 'Sil', onPress: () => resolve(true), style: 'destructive' }
            ]
          );
        });

    if (!confirmDelete) return;

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
        if (Platform.OS === 'web') {
          alert('Plan silindi');
        } else {
          Alert.alert('Başarılı', 'Plan silindi');
        }
        loadPlans(); // Refresh plans
      } else {
        if (Platform.OS === 'web') {
          alert('Plan silinirken bir hata oluştu');
        } else {
          Alert.alert('Hata', 'Plan silinirken bir hata oluştu');
        }
      }
    } catch (error) {
      console.error('Plan silme hatası:', error);
      if (Platform.OS === 'web') {
        alert('Bağlantı hatası');
      } else {
        Alert.alert('Hata', 'Bağlantı hatası');
      }
    }
  };

  const loadPlans = async () => {
    setIsLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) {
        router.replace('/auth/login');
        return;
      }

      const endpoint = activeTab === 'daily' ? 'daily' : 'monthly';
      const response = await fetch(`${BACKEND_URL}/api/plans/${endpoint}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPlans(data);
      } else if (response.status === 401) {
        Alert.alert('Hata', 'Oturum süresi dolmuş. Lütfen tekrar giriş yapın.');
        router.replace('/auth/login');
      } else {
        console.error('Failed to load plans:', response.status);
      }
    } catch (error) {
      console.error('Error loading plans:', error);
      Alert.alert('Hata', 'Planlar yüklenirken bir hata oluştu');
    } finally {
      setIsLoading(false);
    }
  };

  const createNewPlan = () => {
    router.push('/(tabs)/chat');
  };

  const viewPlan = (planId: string) => {
    router.push(`/plan/${planId}?type=${activeTab}`);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatAgeBand = (ageBand: string) => {
    switch (ageBand) {
      case '36_48':
        return '36-48 Ay';
      case '48_60':
        return '48-60 Ay';
      case '60_72':
        return '60-72 Ay';
      default:
        return ageBand;
    }
  };

  const currentPlans = plans.filter(plan => 
    activeTab === 'daily' ? plan.date : plan.month
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>📋 Planlarım</Text>
        <TouchableOpacity onPress={createNewPlan} style={styles.addButton}>
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <View style={styles.tabsContainer}>
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

      <ScrollView style={styles.content}>
        {isLoading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#3498db" />
            <Text style={styles.loadingText}>Planlar yükleniyor...</Text>
          </View>
        ) : currentPlans.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="document-outline" size={64} color="#bdc3c7" />
            <Text style={styles.emptyTitle}>Henüz plan bulunmuyor</Text>
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
                  
                  {Platform.OS === 'web' ? (
                    <button
                      style={{
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        border: 'none',
                        borderRadius: 6,
                        padding: '8px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        cursor: 'pointer',
                        marginRight: 16,
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        deletePlan(plan.id, activeTab as 'daily' | 'monthly');
                      }}
                    >
                      <Ionicons name="trash-outline" size={20} color="#e74c3c" />
                      <span style={{ fontSize: 14, color: '#e74c3c', marginLeft: 4, fontWeight: '500' }}>
                        Sil
                      </span>
                    </button>
                  ) : (
                    <TouchableOpacity 
                      style={[styles.actionButton, styles.deleteButton]}
                      onPress={(e) => {
                        e.stopPropagation();
                        deletePlan(plan.id, activeTab as 'daily' | 'monthly');
                      }}
                      accessibilityRole="button"
                    >
                      <Ionicons name="trash-outline" size={20} color="#e74c3c" />
                      <Text style={[styles.actionButtonText, styles.deleteText]}>Sil</Text>
                    </TouchableOpacity>
                  )}
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
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  addButton: {
    backgroundColor: '#27ae60',
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  tabsContainer: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  tab: {
    flex: 1,
    paddingVertical: 15,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  activeTab: {
    borderBottomColor: '#3498db',
  },
  tabText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#7f8c8d',
  },
  activeTabText: {
    color: '#3498db',
    fontWeight: '600',
  },
  content: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#7f8c8d',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    paddingTop: 100,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#7f8c8d',
    marginTop: 20,
    marginBottom: 10,
  },
  emptySubtitle: {
    fontSize: 16,
    color: '#95a5a6',
    textAlign: 'center',
    marginBottom: 30,
    lineHeight: 24,
  },
  createButton: {
    backgroundColor: '#3498db',
    paddingHorizontal: 30,
    paddingVertical: 15,
    borderRadius: 10,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  plansList: {
    padding: 20,
  },
  planCard: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 12,
    marginBottom: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  planHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 15,
  },
  planTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2c3e50',
    flex: 1,
    marginRight: 10,
  },
  planAgeBand: {
    backgroundColor: '#3498db',
    color: '#fff',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    fontSize: 12,
    fontWeight: '600',
  },
  planInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  planInfoItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  planInfoText: {
    marginLeft: 5,
    fontSize: 14,
    color: '#7f8c8d',
  },
  planActions: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
    marginBottom: 10,
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