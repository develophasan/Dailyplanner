import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || 'https://d7ae705b-7e8b-4812-a515-fa717748a941.preview.emergentagent.com';

export default function HomeScreen() {
  const [isLoading, setIsLoading] = useState(true);
  const [navigationInProgress, setNavigationInProgress] = useState(false);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      console.log('Checking auth status, BACKEND_URL:', BACKEND_URL);
      
      // Check if navigation is already in progress to prevent race conditions
      const navState = await AsyncStorage.getItem('navigationInProgress');
      if (navState === 'true') {
        console.log('Navigation already in progress, skipping auth check');
        setIsLoading(false);
        return;
      }
      
      const token = await AsyncStorage.getItem('authToken');
      console.log('Token from storage:', token ? 'exists' : 'none');
      
      if (token) {
        // Add timeout to fetch request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout
        
        try {
          // Verify token with backend
          const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          console.log('Auth response status:', response.status);
          
          if (response.ok) {
            // User is authenticated, redirect to main app
            console.log('User authenticated, redirecting...');
            setNavigationInProgress(true);
            await AsyncStorage.setItem('navigationInProgress', 'true');
            router.replace('/(tabs)/chat');
            return;
          } else {
            // Token is invalid, remove it
            console.log('Token invalid, removing...');
            await AsyncStorage.removeItem('authToken');
            await AsyncStorage.removeItem('user');
            await AsyncStorage.removeItem('navigationInProgress');
          }
        } catch (fetchError) {
          clearTimeout(timeoutId);
          console.error('Fetch error:', fetchError);
          // If fetch fails, treat as unauthenticated but don't remove existing token
          // in case it's a temporary network issue
          await AsyncStorage.removeItem('navigationInProgress');
        }
      }
    } catch (error) {
      console.error('Auth check error:', error);
      await AsyncStorage.removeItem('navigationInProgress');
      // If there's an error, treat as unauthenticated
    }
    
    setIsLoading(false);
  };

  const handleLogin = () => {
    router.push('/auth/login');
  };

  const handleRegister = () => {
    router.push('/auth/register');
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Yükleniyor...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Ionicons name="school-outline" size={80} color="#3498db" />
          <Text style={styles.title}>MaarifPlanner</Text>
          <Text style={styles.subtitle}>
            Türkiye Yüzyılı Maarif Modeli ile AI Destekli Eğitim Planlama
          </Text>
        </View>

        <View style={styles.features}>
          <View style={styles.feature}>
            <Ionicons name="calendar-outline" size={24} color="#27ae60" />
            <Text style={styles.featureText}>Günlük ve Aylık Plan Oluşturma</Text>
          </View>
          
          <View style={styles.feature}>
            <Ionicons name="chatbubble-outline" size={24} color="#e74c3c" />
            <Text style={styles.featureText}>AI Destekli Plan Asistanı</Text>
          </View>
          
          <View style={styles.feature}>
            <Ionicons name="search-outline" size={24} color="#f39c12" />
            <Text style={styles.featureText}>Matrix Arama ve Keşif</Text>
          </View>
          
          <View style={styles.feature}>
            <Ionicons name="document-text-outline" size={24} color="#9b59b6" />
            <Text style={styles.featureText}>Plan Arşivi ve Yönetimi</Text>
          </View>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
            <Text style={styles.loginButtonText}>Giriş Yap</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.registerButton} onPress={handleRegister}>
            <Text style={styles.registerButtonText}>Kayıt Ol</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.footerText}>
          Milli Eğitim Bakanlığı Okul Öncesi Eğitim Programı ile uyumlu
        </Text>
      </View>
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
    fontSize: 18,
    color: '#7f8c8d',
  },
  content: {
    flex: 1,
    padding: 20,
    justifyContent: 'space-between',
  },
  header: {
    alignItems: 'center',
    marginTop: 40,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginTop: 20,
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 16,
    color: '#7f8c8d',
    textAlign: 'center',
    lineHeight: 24,
    paddingHorizontal: 20,
  },
  features: {
    marginVertical: 40,
  },
  feature: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  featureText: {
    fontSize: 16,
    color: '#2c3e50',
    marginLeft: 15,
    flex: 1,
  },
  actions: {
    marginBottom: 20,
  },
  loginButton: {
    backgroundColor: '#3498db',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  loginButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  registerButton: {
    backgroundColor: 'transparent',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#3498db',
  },
  registerButtonText: {
    color: '#3498db',
    fontSize: 18,
    fontWeight: '600',
  },
  footerText: {
    fontSize: 12,
    color: '#95a5a6',
    textAlign: 'center',
    paddingHorizontal: 20,
    lineHeight: 18,
  },
});