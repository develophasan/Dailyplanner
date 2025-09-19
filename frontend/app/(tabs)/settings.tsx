import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Picker } from '@react-native-picker/picker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';

interface User {
  id: string;
  email: string;
  name: string;
  school?: string;
  className?: string;
  ageDefault?: string;
}

export default function Settings() {
  const [user, setUser] = useState<User | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    school: '',
    className: '',
    ageDefault: '60_72',
  });
  const [notifications, setNotifications] = useState(true);
  const [autoBackup, setAutoBackup] = useState(false);

  useEffect(() => {
    loadUserData();
    loadSettings();
  }, []);

  const loadUserData = async () => {
    try {
      const userData = await AsyncStorage.getItem('user');
      if (userData) {
        const parsedUser = JSON.parse(userData);
        setUser(parsedUser);
        setFormData({
          name: parsedUser.name || '',
          school: parsedUser.school || '',
          className: parsedUser.className || '',
          ageDefault: parsedUser.ageDefault || '60_72',
        });
      }
    } catch (error) {
      console.error('Error loading user data:', error);
    }
  };

  const loadSettings = async () => {
    try {
      const notificationsValue = await AsyncStorage.getItem('notifications');
      const autoBackupValue = await AsyncStorage.getItem('autoBackup');
      
      if (notificationsValue !== null) {
        setNotifications(JSON.parse(notificationsValue));
      }
      if (autoBackupValue !== null) {
        setAutoBackup(JSON.parse(autoBackupValue));
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const saveSettings = async (key: string, value: boolean) => {
    try {
      await AsyncStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };

  const updateFormData = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const saveProfile = async () => {
    try {
      // In a real app, this would send a request to the backend
      const updatedUser = { ...user, ...formData };
      await AsyncStorage.setItem('user', JSON.stringify(updatedUser));
      setUser(updatedUser);
      setEditMode(false);
      Alert.alert('Başarılı', 'Profil bilgileri güncellendi.');
    } catch (error) {
      console.error('Error saving profile:', error);
      Alert.alert('Hata', 'Profil güncellenirken hata oluştu.');
    }
  };

  const logout = () => {
    Alert.alert(
      'Çıkış Yap',
      'Hesabınızdan çıkmak istediğinize emin misiniz?',
      [
        { text: 'İptal', style: 'cancel' },
        {
          text: 'Çıkış Yap',
          style: 'destructive',
          onPress: async () => {
            try {
              await AsyncStorage.multiRemove(['authToken', 'user']);
              router.replace('/');
            } catch (error) {
              console.error('Logout error:', error);
            }
          },
        },
      ]
    );
  };

  const clearCache = () => {
    Alert.alert(
      'Önbellek Temizle',
      'Uygulama önbelleği temizlenecek. Devam edilsin mi?',
      [
        { text: 'İptal', style: 'cancel' },
        {
          text: 'Temizle',
          onPress: async () => {
            try {
              // Clear specific cache items (keep auth data)
              await AsyncStorage.multiRemove(['recentMatrixSearches']);
              Alert.alert('Başarılı', 'Önbellek temizlendi.');
            } catch (error) {
              Alert.alert('Hata', 'Önbellek temizlenirken hata oluştu.');
            }
          },
        },
      ]
    );
  };

  const exportData = () => {
    Alert.alert(
      'Veri Dışa Aktar',
      'Bu özellik yakında eklenecek. Tüm planlarınızı JSON formatında dışa aktarabileceksiniz.',
      [{ text: 'Tamam' }]
    );
  };

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text>Yükleniyor...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Ayarlar</Text>
        {editMode ? (
          <View style={styles.headerActions}>
            <TouchableOpacity onPress={() => setEditMode(false)} style={styles.headerButton}>
              <Text style={styles.headerButtonText}>İptal</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={saveProfile} style={styles.headerButton}>
              <Text style={[styles.headerButtonText, styles.saveButtonText]}>Kaydet</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <TouchableOpacity onPress={() => setEditMode(true)} style={styles.headerButton}>
            <Ionicons name="create-outline" size={24} color="#3498db" />
          </TouchableOpacity>
        )}
      </View>

      <ScrollView style={styles.content}>
        {/* Profile Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Profil Bilgileri</Text>
          
          <View style={styles.profileCard}>
            <View style={styles.inputContainer}>
              <Text style={styles.label}>Ad Soyad</Text>
              <TextInput
                style={[styles.input, !editMode && styles.disabledInput]}
                value={formData.name}
                onChangeText={(value) => updateFormData('name', value)}
                editable={editMode}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>E-posta</Text>
              <TextInput
                style={[styles.input, styles.disabledInput]}
                value={user.email}
                editable={false}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Okul</Text>
              <TextInput
                style={[styles.input, !editMode && styles.disabledInput]}
                value={formData.school}
                onChangeText={(value) => updateFormData('school', value)}
                placeholder="Okulunuzun adı"
                editable={editMode}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Sınıf</Text>
              <TextInput
                style={[styles.input, !editMode && styles.disabledInput]}
                value={formData.className}
                onChangeText={(value) => updateFormData('className', value)}
                placeholder="Sınıf adı"
                editable={editMode}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Varsayılan Yaş Bandı</Text>
              {editMode ? (
                <View style={styles.pickerContainer}>
                  <Picker
                    selectedValue={formData.ageDefault}
                    onValueChange={(value) => updateFormData('ageDefault', value)}
                    style={styles.picker}
                  >
                    <Picker.Item label="36-48 Ay" value="36_48" />
                    <Picker.Item label="48-60 Ay" value="48_60" />
                    <Picker.Item label="60-72 Ay" value="60_72" />
                  </Picker>
                </View>
              ) : (
                <TextInput
                  style={[styles.input, styles.disabledInput]}
                  value={formData.ageDefault === '36_48' ? '36-48 Ay' : formData.ageDefault === '48_60' ? '48-60 Ay' : '60-72 Ay'}
                  editable={false}
                />
              )}
            </View>
          </View>
        </View>

        {/* App Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Uygulama Ayarları</Text>
          
          <View style={styles.settingCard}>
            <View style={styles.settingItem}>
              <View style={styles.settingInfo}>
                <Text style={styles.settingTitle}>Bildirimler</Text>
                <Text style={styles.settingDescription}>
                  Plan hatırlatmaları ve güncellemeler
                </Text>
              </View>
              <Switch
                value={notifications}
                onValueChange={(value) => {
                  setNotifications(value);
                  saveSettings('notifications', value);
                }}
              />
            </View>

            <View style={styles.settingItem}>
              <View style={styles.settingInfo}>
                <Text style={styles.settingTitle}>Otomatik Yedekleme</Text>
                <Text style={styles.settingDescription}>
                  Planları otomatik olarak yedekle
                </Text>
              </View>
              <Switch
                value={autoBackup}
                onValueChange={(value) => {
                  setAutoBackup(value);
                  saveSettings('autoBackup', value);
                }}
              />
            </View>
          </View>
        </View>

        {/* Data Management */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Veri Yönetimi</Text>
          
          <TouchableOpacity style={styles.actionCard} onPress={exportData}>
            <Ionicons name="download-outline" size={24} color="#3498db" />
            <View style={styles.actionInfo}>
              <Text style={styles.actionTitle}>Veri Dışa Aktar</Text>
              <Text style={styles.actionDescription}>
                Tüm planlarınızı JSON formatında dışa aktarın
              </Text>
            </View>
            <Ionicons name="chevron-forward-outline" size={20} color="#bdc3c7" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionCard} onPress={clearCache}>
            <Ionicons name="trash-outline" size={24} color="#f39c12" />
            <View style={styles.actionInfo}>
              <Text style={styles.actionTitle}>Önbellek Temizle</Text>
              <Text style={styles.actionDescription}>
                Geçici dosyaları ve önbelleği temizle
              </Text>
            </View>
            <Ionicons name="chevron-forward-outline" size={20} color="#bdc3c7" />
          </TouchableOpacity>
        </View>

        {/* Account Actions */}
        <View style={styles.section}>
          <TouchableOpacity style={[styles.actionCard, styles.logoutCard]} onPress={logout}>
            <Ionicons name="log-out-outline" size={24} color="#e74c3c" />
            <View style={styles.actionInfo}>
              <Text style={[styles.actionTitle, styles.logoutText]}>Çıkış Yap</Text>
              <Text style={styles.actionDescription}>
                Hesabınızdan güvenli şekilde çıkış yapın
              </Text>
            </View>
            <Ionicons name="chevron-forward-outline" size={20} color="#bdc3c7" />
          </TouchableOpacity>
        </View>

        {/* App Info */}
        <View style={styles.section}>
          <Text style={styles.appInfo}>
            MaarifPlanner v1.0.0{'\n'}
            Türkiye Yüzyılı Maarif Modeli
          </Text>
        </View>
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
  headerActions: {
    flexDirection: 'row',
  },
  headerButton: {
    padding: 4,
    marginLeft: 12,
  },
  headerButtonText: {
    fontSize: 16,
    color: '#3498db',
    fontWeight: '500',
  },
  saveButtonText: {
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 12,
    paddingHorizontal: 16,
  },
  profileCard: {
    backgroundColor: 'white',
    marginHorizontal: 16,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  inputContainer: {
    marginBottom: 16,
  },
  label: {
    fontSize: 16,
    fontWeight: '500',
    color: '#2c3e50',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e1e8ed',
  },
  disabledInput: {
    color: '#7f8c8d',
    backgroundColor: '#ecf0f1',
  },
  pickerContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e1e8ed',
  },
  picker: {
    height: 48,
  },
  settingCard: {
    backgroundColor: 'white',
    marginHorizontal: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  settingInfo: {
    flex: 1,
    marginRight: 16,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 4,
  },
  settingDescription: {
    fontSize: 14,
    color: '#7f8c8d',
  },
  actionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    marginHorizontal: 16,
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  actionInfo: {
    flex: 1,
    marginLeft: 16,
    marginRight: 8,
  },
  actionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 4,
  },
  actionDescription: {
    fontSize: 14,
    color: '#7f8c8d',
  },
  logoutCard: {
    marginBottom: 16,
  },
  logoutText: {
    color: '#e74c3c',
  },
  appInfo: {
    fontSize: 14,
    color: '#7f8c8d',
    textAlign: 'center',
    paddingHorizontal: 16,
    lineHeight: 20,
  },
});