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
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

interface PlanDetail {
  id: string;
  date: string;
  ageBand: string;
  title: string;
  planJson: any;
  createdAt: string;
  pdfUrl?: string;
}

export default function PlanDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'activities' | 'assessment'>('overview');

  useEffect(() => {
    if (id) {
      loadPlan();
    }
  }, [id]);

  const getAuthToken = async () => {
    return await AsyncStorage.getItem('authToken');
  };

  const loadPlan = async () => {
    setIsLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) {
        router.replace('/auth/login');
        return;
      }

      const response = await fetch(`${BACKEND_URL}/api/plans/daily/${id}`, {
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
        if (response.status === 404) {
          Alert.alert('Hata', 'Plan bulunamadı.');
          router.back();
          return;
        }
        throw new Error('Plan yüklenemedi');
      }

      const planData = await response.json();
      setPlan(planData);
    } catch (error) {
      console.error('Load plan error:', error);
      Alert.alert('Hata', 'Plan yüklenirken hata oluştu.');
      router.back();
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('tr-TR', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatAgeBand = (ageBand: string) => {
    const ageMap: { [key: string]: string } = {
      '36_48': '36-48 Ay',
      '48_60': '48-60 Ay',
      '60_72': '60-72 Ay',
    };
    return ageMap[ageBand] || ageBand;
  };

  const downloadPDF = () => {
    Alert.alert(
      'PDF İndir',
      'PDF oluşturma özelliği yakında eklenecek.',
      [{ text: 'Tamam' }]
    );
  };

  const sharePlan = () => {
    Alert.alert(
      'Plan Paylaş',
      'Plan paylaşma özelliği yakında eklenecek.',
      [{ text: 'Tamam' }]
    );
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#3498db" />
          <Text style={styles.loadingText}>Plan yükleniyor...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!plan) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle-outline" size={64} color="#e74c3c" />
          <Text style={styles.errorText}>Plan bulunamadı</Text>
        </View>
      </SafeAreaView>
    );
  }

  const renderOverview = () => (
    <View style={styles.tabContent}>
      <View style={styles.infoCard}>
        <Text style={styles.cardTitle}>Plan Bilgileri</Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Tarih:</Text>
          <Text style={styles.infoValue}>{formatDate(plan.date)}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Yaş Bandı:</Text>
          <Text style={styles.infoValue}>{formatAgeBand(plan.ageBand)}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Oluşturma:</Text>
          <Text style={styles.infoValue}>{formatDate(plan.createdAt)}</Text>
        </View>
      </View>

      {plan.planJson?.domainOutcomes && plan.planJson.domainOutcomes.length > 0 && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Hedeflenen Alanlar</Text>
          {plan.planJson.domainOutcomes.map((outcome: any, index: number) => (
            <View key={index} style={styles.outcomeItem}>
              <Text style={styles.outcomeCode}>{outcome.code}</Text>
              {outcome.indicators && outcome.indicators.length > 0 && (
                <View style={styles.indicatorsList}>
                  {outcome.indicators.map((indicator: string, idx: number) => (
                    <Text key={idx} style={styles.indicator}>• {indicator}</Text>
                  ))}
                </View>
              )}
            </View>
          ))}
        </View>
      )}

      {plan.planJson?.conceptualSkills && plan.planJson.conceptualSkills.length > 0 && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Kavramsal Beceriler</Text>
          {plan.planJson.conceptualSkills.map((skill: string, index: number) => (
            <Text key={index} style={styles.listItem}>• {skill}</Text>
          ))}
        </View>
      )}

      {plan.planJson?.dispositions && plan.planJson.dispositions.length > 0 && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Eğilimler</Text>
          {plan.planJson.dispositions.map((disposition: string, index: number) => (
            <Text key={index} style={styles.listItem}>• {disposition}</Text>
          ))}
        </View>
      )}
    </View>
  );

  const renderActivities = () => (
    <View style={styles.tabContent}>
      {plan.planJson?.blocks?.startOfDay && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Güne Başlama</Text>
          <Text style={styles.contentText}>{plan.planJson.blocks.startOfDay}</Text>
        </View>
      )}

      {plan.planJson?.blocks?.learningCenters && plan.planJson.blocks.learningCenters.length > 0 && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Öğrenme Merkezleri</Text>
          {plan.planJson.blocks.learningCenters.map((center: string, index: number) => (
            <Text key={index} style={styles.listItem}>• {center}</Text>
          ))}
        </View>
      )}

      {plan.planJson?.blocks?.activities && plan.planJson.blocks.activities.length > 0 && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Etkinlikler</Text>
          {plan.planJson.blocks.activities.map((activity: any, index: number) => (
            <View key={index} style={styles.activityItem}>
              <Text style={styles.activityTitle}>{index + 1}. {activity.title}</Text>
              
              {activity.location && (
                <Text style={styles.activityLocation}>📍 {activity.location}</Text>
              )}
              
              {activity.materials && activity.materials.length > 0 && (
                <View style={styles.activitySection}>
                  <Text style={styles.activitySectionTitle}>Materyaller:</Text>
                  {activity.materials.map((material: string, idx: number) => (
                    <Text key={idx} style={styles.activityItem}>• {material}</Text>
                  ))}
                </View>
              )}
              
              {activity.steps && activity.steps.length > 0 && (
                <View style={styles.activitySection}>
                  <Text style={styles.activitySectionTitle}>Adımlar:</Text>
                  {activity.steps.map((step: string, idx: number) => (
                    <Text key={idx} style={styles.activityItem}>{idx + 1}. {step}</Text>
                  ))}
                </View>
              )}
            </View>
          ))}
        </View>
      )}

      {plan.planJson?.blocks?.mealsCleanup && plan.planJson.blocks.mealsCleanup.length > 0 && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Beslenme & Temizlik</Text>
          {plan.planJson.blocks.mealsCleanup.map((item: string, index: number) => (
            <Text key={index} style={styles.listItem}>• {item}</Text>
          ))}
        </View>
      )}
    </View>
  );

  const renderAssessment = () => (
    <View style={styles.tabContent}>
      {plan.planJson?.blocks?.assessment && plan.planJson.blocks.assessment.length > 0 && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Değerlendirme</Text>
          {plan.planJson.blocks.assessment.map((item: string, index: number) => (
            <Text key={index} style={styles.listItem}>• {item}</Text>
          ))}
        </View>
      )}

      {plan.planJson?.notes && (
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Notlar</Text>
          <Text style={styles.contentText}>{plan.planJson.notes}</Text>
        </View>
      )}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#3498db" />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {plan.title}
        </Text>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={sharePlan} style={styles.actionButton}>
            <Ionicons name="share-outline" size={24} color="#3498db" />
          </TouchableOpacity>
          <TouchableOpacity onPress={downloadPDF} style={styles.actionButton}>
            <Ionicons name="download-outline" size={24} color="#3498db" />
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'overview' && styles.activeTab]}
          onPress={() => setActiveTab('overview')}
        >
          <Text style={[styles.tabText, activeTab === 'overview' && styles.activeTabText]}>
            Genel
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'activities' && styles.activeTab]}
          onPress={() => setActiveTab('activities')}
        >
          <Text style={[styles.tabText, activeTab === 'activities' && styles.activeTabText]}>
            Etkinlikler
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'assessment' && styles.activeTab]}
          onPress={() => setActiveTab('assessment')}
        >
          <Text style={[styles.tabText, activeTab === 'assessment' && styles.activeTabText]}>
            Değerlendirme
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'activities' && renderActivities()}
        {activeTab === 'assessment' && renderAssessment()}
      </ScrollView>
    </SafeAreaView>
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
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#7f8c8d',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorText: {
    marginTop: 16,
    fontSize: 18,
    color: '#e74c3c',
    fontWeight: 'bold',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  backButton: {
    marginRight: 12,
  },
  headerTitle: {
    flex: 1,
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  headerActions: {
    flexDirection: 'row',
  },
  actionButton: {
    marginLeft: 8,
    padding: 4,
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
  content: {
    flex: 1,
  },
  tabContent: {
    padding: 16,
  },
  infoCard: {
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
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#7f8c8d',
    width: 80,
  },
  infoValue: {
    fontSize: 16,
    color: '#2c3e50',
    flex: 1,
  },
  outcomeItem: {
    marginBottom: 12,
  },
  outcomeCode: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#3498db',
    marginBottom: 4,
  },
  indicatorsList: {
    marginLeft: 16,
  },
  indicator: {
    fontSize: 14,
    color: '#7f8c8d',
    marginBottom: 2,
  },
  listItem: {
    fontSize: 16,
    color: '#2c3e50',
    marginBottom: 4,
    lineHeight: 22,
  },
  contentText: {
    fontSize: 16,
    color: '#2c3e50',
    lineHeight: 24,
  },
  activityItem: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  activityTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
  },
  activityLocation: {
    fontSize: 14,
    color: '#7f8c8d',
    marginBottom: 8,
  },
  activitySection: {
    marginTop: 8,
  },
  activitySectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 4,
  },
});