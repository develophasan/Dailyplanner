import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Modal,
  Image,
  TextInput,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as ImagePicker from 'expo-image-picker';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

interface PlanDetail {
  id: string;
  date: string;
  ageBand: string;
  title: string;
  planJson: any;
  createdAt: string;
  pdfUrl?: string;
}

interface PortfolioPhoto {
  id: string;
  activityTitle: string;
  photoBase64: string;
  description?: string;
  uploadedAt: string;
}

export default function PlanDetail() {
  const { id, type } = useLocalSearchParams<{ id: string; type?: string }>();
  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'activities' | 'assessment' | 'portfolio'>('overview');
  const [portfolioPhotos, setPortfolioPhotos] = useState<PortfolioPhoto[]>([]);
  const [isPortfolioLoading, setIsPortfolioLoading] = useState(false);
  const [showPortfolioModal, setShowPortfolioModal] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState('');
  const [photoDescription, setPhotoDescription] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (id) {
      loadPlan();
      loadPortfolioPhotos();
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

      const endpoint = type === 'monthly' ? 'monthly' : 'daily';
      const response = await fetch(`${BACKEND_URL}/api/plans/${endpoint}/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPlan(data);
      } else {
        Alert.alert('Hata', 'Plan yüklenirken bir hata oluştu');
      }
    } catch (error) {
      console.error('Plan yükleme hatası:', error);
      Alert.alert('Hata', 'Bağlantı hatası');
    } finally {
      setIsLoading(false);
    }
  };

  const loadPortfolioPhotos = async () => {
    if (type === 'monthly') return; // Portfolio only for daily plans
    
    setIsPortfolioLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) return;

      const response = await fetch(`${BACKEND_URL}/api/plans/daily/${id}/portfolio`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPortfolioPhotos(data);
      }
    } catch (error) {
      console.error('Portfolio yükleme hatası:', error);
    } finally {
      setIsPortfolioLoading(false);
    }
  };

  const handleDeletePlan = () => {
    Alert.alert(
      'Planı Sil',
      'Bu planı silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.',
      [
        { text: 'İptal', style: 'cancel' },
        { 
          text: 'Sil', 
          style: 'destructive',
          onPress: deletePlan
        }
      ]
    );
  };

  const deletePlan = async () => {
    try {
      const token = await getAuthToken();
      if (!token) return;

      const endpoint = type === 'monthly' ? 'monthly' : 'daily';
      const response = await fetch(`${BACKEND_URL}/api/plans/${endpoint}/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        Alert.alert('Başarılı', 'Plan silindi', [
          { text: 'Tamam', onPress: () => router.back() }
        ]);
      } else {
        Alert.alert('Hata', 'Plan silinirken bir hata oluştu');
      }
    } catch (error) {
      console.error('Plan silme hatası:', error);
      Alert.alert('Hata', 'Bağlantı hatası');
    }
  };

  const handleAddPortfolio = () => {
    if (!plan?.planJson?.blocks?.activities || plan.planJson.blocks.activities.length === 0) {
      Alert.alert('Bilgi', 'Bu planda etkinlik bulunmuyor');
      return;
    }
    setShowPortfolioModal(true);
  };

  const pickImage = async () => {
    if (Platform.OS === 'web') {
      // Web için HTML file input kullan
      try {
        const input = (document as any).createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = (event: any) => {
          const file = event.target.files[0];
          if (file) {
            const reader = new FileReader();
            reader.onload = (e: any) => {
              const base64 = e.target.result.split(',')[1]; // Remove data:image/jpeg;base64, prefix
              uploadPhoto(base64);
            };
            reader.readAsDataURL(file);
          }
        };
        input.click();
      } catch (error) {
        console.error('Web file picker error:', error);
        if (Platform.OS === 'web') {
          alert('Fotoğraf seçme özelliği bu tarayıcıda desteklenmiyor');
        } else {
          Alert.alert('Hata', 'Fotoğraf seçme işlemi başarısız');
        }
      }
      return;
    }

    const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (permissionResult.granted === false) {
      Alert.alert('İzin Gerekli', 'Galeriye erişim izni vermeniz gerekiyor');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      uploadPhoto(result.assets[0].base64);
    }
  };

  const uploadPhoto = async (base64Image: string) => {
    if (!selectedActivity) {
      Alert.alert('Hata', 'Lütfen bir etkinlik seçin');
      return;
    }

    setIsUploading(true);
    try {
      const token = await getAuthToken();
      if (!token) return;

      const response = await fetch(`${BACKEND_URL}/api/plans/daily/${id}/portfolio`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          planId: id,
          activityTitle: selectedActivity,
          photoBase64: `data:image/jpeg;base64,${base64Image}`,
          description: photoDescription,
        }),
      });

      if (response.ok) {
        Alert.alert('Başarılı', 'Fotoğraf eklendi');
        setShowPortfolioModal(false);
        setSelectedActivity('');
        setPhotoDescription('');
        loadPortfolioPhotos(); // Refresh portfolio
      } else {
        Alert.alert('Hata', 'Fotoğraf yüklenirken bir hata oluştu');
      }
    } catch (error) {
      console.error('Fotoğraph upload hatası:', error);
      Alert.alert('Hata', 'Bağlantı hatası');
    } finally {
      setIsUploading(false);
    }
  };

  const deletePortfolioPhoto = async (photoId: string) => {
    Alert.alert(
      'Fotoğrafı Sil',
      'Bu fotoğrafı silmek istediğinizden emin misiniz?',
      [
        { text: 'İptal', style: 'cancel' },
        { 
          text: 'Sil', 
          style: 'destructive',
          onPress: async () => {
            try {
              const token = await getAuthToken();
              if (!token) return;

              const response = await fetch(`${BACKEND_URL}/api/portfolio/${photoId}`, {
                method: 'DELETE',
                headers: {
                  'Authorization': `Bearer ${token}`,
                },
              });

              if (response.ok) {
                loadPortfolioPhotos(); // Refresh portfolio
              } else {
                Alert.alert('Hata', 'Fotoğraf silinirken bir hata oluştu');
              }
            } catch (error) {
              console.error('Portfolio photo delete error:', error);
            }
          }
        }
      ]
    );
  };

  const renderOverview = () => {
    if (!plan?.planJson) return null;

    const planData = plan.planJson;
    
    return (
      <View style={styles.tabContent}>
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>📋 Plan Bilgileri</Text>
          <Text style={styles.infoText}>📅 Tarih: {plan.date}</Text>
          <Text style={styles.infoText}>👶 Yaş Grubu: {plan.ageBand}</Text>
          <Text style={styles.infoText}>🎯 Tema: {planData.theme || 'Belirtilmemiş'}</Text>
          {planData.duration && (
            <Text style={styles.infoText}>⏰ Süre: {planData.duration}</Text>
          )}
        </View>

        {planData.domainOutcomes && planData.domainOutcomes.length > 0 && (
          <View style={styles.infoCard}>
            <Text style={styles.cardTitle}>🎯 Alan Becerileri</Text>
            {planData.domainOutcomes.map((domain: any, index: number) => (
              <View key={index} style={styles.domainItem}>
                <Text style={styles.domainCode}>{domain.code}</Text>
                {domain.indicators && domain.indicators.length > 0 && (
                  <View style={styles.indicatorsList}>
                    {domain.indicators.map((indicator: string, idx: number) => (
                      <Text key={idx} style={styles.indicator}>• {indicator}</Text>
                    ))}
                  </View>
                )}
                {domain.notes && (
                  <Text style={styles.domainNotes}>💡 {domain.notes}</Text>
                )}
              </View>
            ))}
          </View>
        )}

        {planData.conceptualSkills && planData.conceptualSkills.length > 0 && (
          <View style={styles.infoCard}>
            <Text style={styles.cardTitle}>🧠 Kavramsal Beceriler</Text>
            {planData.conceptualSkills.map((skill: string, index: number) => (
              <Text key={index} style={styles.skillItem}>• {skill}</Text>
            ))}
          </View>
        )}

        {planData.dispositions && planData.dispositions.length > 0 && (
          <View style={styles.infoCard}>
            <Text style={styles.cardTitle}>💫 Eğilimler</Text>
            {planData.dispositions.map((disposition: string, index: number) => (
              <Text key={index} style={styles.skillItem}>• {disposition}</Text>
            ))}
          </View>
        )}
      </View>
    );
  };

  const renderActivities = () => {
    if (!plan?.planJson?.blocks?.activities) return null;

    const activities = plan.planJson.blocks.activities;

    return (
      <View style={styles.tabContent}>
        {activities.map((activity: any, index: number) => (
          <View key={index} style={styles.activityCard}>
            <Text style={styles.activityTitle}>🎨 {activity.title}</Text>
            
            <View style={styles.activityInfo}>
              <Text style={styles.activityMeta}>📍 Yer: {activity.location}</Text>
              <Text style={styles.activityMeta}>⏱️ Süre: {activity.duration}</Text>
            </View>

            {activity.materials && activity.materials.length > 0 && (
              <View style={styles.activitySection}>
                <Text style={styles.sectionTitle}>🧰 Malzemeler:</Text>
                {activity.materials.map((material: string, idx: number) => (
                  <Text key={idx} style={styles.listItem}>• {material}</Text>
                ))}
              </View>
            )}

            {activity.steps && activity.steps.length > 0 && (
              <View style={styles.activitySection}>
                <Text style={styles.sectionTitle}>📝 Adımlar:</Text>
                {activity.steps.map((step: string, idx: number) => (
                  <Text key={idx} style={styles.stepItem}>{idx + 1}. {step}</Text>
                ))}
              </View>
            )}

            {activity.objectives && activity.objectives.length > 0 && (
              <View style={styles.activitySection}>
                <Text style={styles.sectionTitle}>🎯 Hedefler:</Text>
                {activity.objectives.map((objective: string, idx: number) => (
                  <Text key={idx} style={styles.listItem}>• {objective}</Text>
                ))}
              </View>
            )}

            {activity.differentiation && (
              <View style={styles.activitySection}>
                <Text style={styles.sectionTitle}>🔄 Farklılaştırma:</Text>
                <Text style={styles.differentiationText}>{activity.differentiation}</Text>
              </View>
            )}
          </View>
        ))}
      </View>
    );
  };

  const renderAssessment = () => {
    if (!plan?.planJson?.blocks?.assessment) return null;

    const assessmentMethods = plan.planJson.blocks.assessment;

    return (
      <View style={styles.tabContent}>
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>📊 Değerlendirme Yöntemleri</Text>
          {assessmentMethods.map((method: string, index: number) => (
            <Text key={index} style={styles.assessmentItem}>
              {index + 1}. {method}
            </Text>
          ))}
        </View>

        {plan.planJson.blocks.mealsCleanup && plan.planJson.blocks.mealsCleanup.length > 0 && (
          <View style={styles.infoCard}>
            <Text style={styles.cardTitle}>🍎 Beslenme & Temizlik</Text>
            {plan.planJson.blocks.mealsCleanup.map((item: string, index: number) => (
              <Text key={index} style={styles.assessmentItem}>• {item}</Text>
            ))}
          </View>
        )}

        {plan.planJson.differentiation && (
          <View style={styles.infoCard}>
            <Text style={styles.cardTitle}>🔄 Genel Farklılaştırma</Text>
            {plan.planJson.differentiation.enrichment && (
              <View style={styles.diffSection}>
                <Text style={styles.diffTitle}>✨ Zenginleştirme:</Text>
                <Text style={styles.diffText}>{plan.planJson.differentiation.enrichment}</Text>
              </View>
            )}
            {plan.planJson.differentiation.support && (
              <View style={styles.diffSection}>
                <Text style={styles.diffTitle}>🤝 Destek:</Text>
                <Text style={styles.diffText}>{plan.planJson.differentiation.support}</Text>
              </View>
            )}
          </View>
        )}
      </View>
    );
  };

  const renderPortfolio = () => {
    if (type === 'monthly') {
      return (
        <View style={styles.tabContent}>
          <Text style={styles.noPortfolioText}>
            Portfolyo özelliği sadece günlük planlar için kullanılabilir.
          </Text>
        </View>
      );
    }

    return (
      <View style={styles.tabContent}>
        <View style={styles.portfolioHeader}>
          <Text style={styles.cardTitle}>📸 Etkinlik Portfolyosu</Text>
          <TouchableOpacity 
            style={styles.addPhotoButton}
            onPress={handleAddPortfolio}
          >
            <Ionicons name="camera" size={20} color="#fff" />
            <Text style={styles.addPhotoText}>Fotoğraf Ekle</Text>
          </TouchableOpacity>
        </View>

        {isPortfolioLoading ? (
          <ActivityIndicator size="large" color="#3498db" style={styles.portfolioLoading} />
        ) : portfolioPhotos.length === 0 ? (
          <View style={styles.noPhotosContainer}>
            <Ionicons name="images-outline" size={64} color="#bdc3c7" />
            <Text style={styles.noPhotosText}>Henüz fotoğraf eklenmemiş</Text>
            <TouchableOpacity 
              style={styles.firstPhotoButton}
              onPress={handleAddPortfolio}
            >
              <Text style={styles.firstPhotoButtonText}>İlk Fotoğrafı Ekle</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.portfolioScroll}>
            {portfolioPhotos.map((photo) => (
              <View key={photo.id} style={styles.photoCard}>
                <Image source={{ uri: photo.photoBase64 }} style={styles.portfolioImage} />
                <View style={styles.photoInfo}>
                  <Text style={styles.photoActivity}>{photo.activityTitle}</Text>
                  {photo.description && (
                    <Text style={styles.photoDescription}>{photo.description}</Text>
                  )}
                  <Text style={styles.photoDate}>
                    {new Date(photo.uploadedAt).toLocaleDateString('tr-TR')}
                  </Text>
                </View>
                <TouchableOpacity 
                  style={styles.deletePhotoButton}
                  onPress={() => deletePortfolioPhoto(photo.id)}
                  accessibilityRole="button"
                  {...(Platform.OS === 'web' && {
                    onClick: () => deletePortfolioPhoto(photo.id)
                  })}
                >
                  <Ionicons name="trash-outline" size={16} color="#e74c3c" />
                </TouchableOpacity>
              </View>
            ))}
          </ScrollView>
        )}
      </View>
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
          <Text style={styles.errorText}>Plan bulunamadı</Text>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Text style={styles.backButtonText}>Geri Dön</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const activities = plan.planJson?.blocks?.activities || [];

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backIcon}>
          <Ionicons name="arrow-back" size={24} color="#2c3e50" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{plan.title || 'Plan Detayı'}</Text>
        <TouchableOpacity 
          onPress={handleDeletePlan} 
          style={styles.deleteIcon}
          accessibilityRole="button"
          {...(Platform.OS === 'web' && {
            onClick: handleDeletePlan
          })}
        >
          <Ionicons name="trash-outline" size={24} color="#e74c3c" />
        </TouchableOpacity>
      </View>

      {/* Tabs */}
      <View style={styles.tabsContainer}>
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
        {type !== 'monthly' && (
          <TouchableOpacity
            style={[styles.tab, activeTab === 'portfolio' && styles.activeTab]}
            onPress={() => setActiveTab('portfolio')}
          >
            <Text style={[styles.tabText, activeTab === 'portfolio' && styles.activeTabText]}>
              Portfolyo
            </Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Content */}
      <ScrollView style={styles.content}>
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'activities' && renderActivities()}
        {activeTab === 'assessment' && renderAssessment()}
        {activeTab === 'portfolio' && renderPortfolio()}
      </ScrollView>

      {/* Portfolio Upload Modal */}
      <Modal visible={showPortfolioModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>📸 Portfolyo Fotoğrafı Ekle</Text>
              <TouchableOpacity onPress={() => setShowPortfolioModal(false)}>
                <Ionicons name="close" size={24} color="#2c3e50" />
              </TouchableOpacity>
            </View>

            <Text style={styles.modalLabel}>Etkinlik Seçin:</Text>
            <ScrollView style={styles.activityPicker}>
              {activities.map((activity: any, index: number) => (
                <TouchableOpacity
                  key={index}
                  style={[
                    styles.activityOption,
                    selectedActivity === activity.title && styles.selectedActivity
                  ]}
                  onPress={() => setSelectedActivity(activity.title)}
                >
                  <Text style={[
                    styles.activityOptionText,
                    selectedActivity === activity.title && styles.selectedActivityText
                  ]}>
                    {activity.title}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            <Text style={styles.modalLabel}>Açıklama (İsteğe bağlı):</Text>
            <TextInput
              style={styles.descriptionInput}
              value={photoDescription}
              onChangeText={setPhotoDescription}
              placeholder="Fotoğraf açıklaması..."
              multiline
              numberOfLines={3}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setShowPortfolioModal(false)}
              >
                <Text style={styles.cancelButtonText}>İptal</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.uploadButton, isUploading && styles.disabledButton]}
                onPress={pickImage}
                disabled={isUploading}
              >
                {isUploading ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.uploadButtonText}>Fotoğraf Seç</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 18,
    color: '#e74c3c',
    marginBottom: 20,
  },
  backButton: {
    backgroundColor: '#3498db',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  backButtonText: {
    color: '#fff',
    fontSize: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  backIcon: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    flex: 1,
    textAlign: 'center',
    marginHorizontal: 16,
  },
  deleteIcon: {
    padding: 8,
  },
  tabsContainer: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  activeTab: {
    borderBottomColor: '#3498db',
  },
  tabText: {
    fontSize: 14,
    color: '#7f8c8d',
    fontWeight: '500',
  },
  activeTabText: {
    color: '#3498db',
    fontWeight: '600',
  },
  content: {
    flex: 1,
  },
  tabContent: {
    padding: 16,
  },
  infoCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 12,
  },
  infoText: {
    fontSize: 16,
    color: '#34495e',
    marginBottom: 8,
    lineHeight: 24,
  },
  domainItem: {
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#ecf0f1',
  },
  domainCode: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#3498db',
    marginBottom: 8,
  },
  indicatorsList: {
    marginLeft: 12,
    marginBottom: 8,
  },
  indicator: {
    fontSize: 14,
    color: '#2c3e50',
    marginBottom: 4,
    lineHeight: 20,
  },
  domainNotes: {
    fontSize: 14,
    color: '#7f8c8d',
    fontStyle: 'italic',
  },
  skillItem: {
    fontSize: 15,
    color: '#2c3e50',
    marginBottom: 6,
    lineHeight: 22,
  },
  activityCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  activityTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 12,
  },
  activityInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  activityMeta: {
    fontSize: 14,
    color: '#7f8c8d',
  },
  activitySection: {
    marginTop: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 8,
  },
  listItem: {
    fontSize: 14,
    color: '#34495e',
    marginBottom: 4,
    lineHeight: 20,
  },
  stepItem: {
    fontSize: 14,
    color: '#34495e',
    marginBottom: 6,
    lineHeight: 20,
  },
  differentiationText: {
    fontSize: 14,
    color: '#34495e',
    lineHeight: 20,
    fontStyle: 'italic',
  },
  assessmentItem: {
    fontSize: 15,
    color: '#2c3e50',
    marginBottom: 8,
    lineHeight: 22,
  },
  diffSection: {
    marginBottom: 12,
  },
  diffTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 6,
  },
  diffText: {
    fontSize: 14,
    color: '#34495e',
    lineHeight: 20,
  },
  portfolioHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  addPhotoButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#3498db',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  addPhotoText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
    marginLeft: 6,
  },
  portfolioLoading: {
    marginTop: 50,
  },
  noPhotosContainer: {
    alignItems: 'center',
    paddingVertical: 50,
  },
  noPhotosText: {
    fontSize: 16,
    color: '#7f8c8d',
    marginTop: 16,
    marginBottom: 20,
  },
  firstPhotoButton: {
    backgroundColor: '#3498db',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
  },
  firstPhotoButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
  },
  portfolioScroll: {
    marginTop: 10,
  },
  photoCard: {
    width: 200,
    marginRight: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  portfolioImage: {
    width: 200,
    height: 150,
    borderTopLeftRadius: 12,
    borderTopRightRadius: 12,
  },
  photoInfo: {
    padding: 12,
  },
  photoActivity: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 4,
  },
  photoDescription: {
    fontSize: 12,
    color: '#7f8c8d',
    marginBottom: 6,
  },
  photoDate: {
    fontSize: 11,
    color: '#95a5a6',
  },
  deletePhotoButton: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 15,
    width: 30,
    height: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  noPortfolioText: {
    fontSize: 16,
    color: '#7f8c8d',
    textAlign: 'center',
    marginTop: 50,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    width: '90%',
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  modalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 10,
  },
  activityPicker: {
    maxHeight: 150,
    marginBottom: 20,
  },
  activityOption: {
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e1e8ed',
    marginBottom: 8,
  },
  selectedActivity: {
    backgroundColor: '#3498db',
    borderColor: '#3498db',
  },
  activityOptionText: {
    fontSize: 14,
    color: '#2c3e50',
  },
  selectedActivityText: {
    color: '#fff',
  },
  descriptionInput: {
    borderWidth: 1,
    borderColor: '#e1e8ed',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    textAlignVertical: 'top',
    marginBottom: 20,
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  cancelButton: {
    flex: 1,
    marginRight: 10,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e1e8ed',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    color: '#7f8c8d',
  },
  uploadButton: {
    flex: 1,
    marginLeft: 10,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#3498db',
    alignItems: 'center',
  },
  uploadButtonText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '500',
  },
  disabledButton: {
    backgroundColor: '#bdc3c7',
  },
});