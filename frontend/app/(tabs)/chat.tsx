import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL || 'https://dailyplanner-8.preview.emergentagent.com';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface AIResponse {
  finalize: boolean;
  type: 'daily' | 'monthly';
  ageBand: string;
  date?: string;
  domainOutcomes?: any[];
  blocks?: any;
  followUpQuestions?: string[];
  missingFields?: string[];
  notes?: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [currentResponse, setCurrentResponse] = useState<AIResponse | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const scrollViewRef = useRef<ScrollView>(null);

  useEffect(() => {
    loadUser();
    // Add welcome message
    setMessages([{
      role: 'assistant',
      content: 'Merhaba! Ben MaarifPlanner AI asistanınızım. Günlük veya aylık plan oluşturmanızda size yardımcı olacağım. Hangi yaş bandı için plan oluşturmak istiyorsunuz ve ne tür etkinlikler planlıyorsunuz?',
      timestamp: new Date().toISOString(),
    }]);
  }, []);

  const loadUser = async () => {
    try {
      const userData = await AsyncStorage.getItem('user');
      if (userData) {
        setUser(JSON.parse(userData));
      }
    } catch (error) {
      console.error('Error loading user:', error);
    }
  };

  const getAuthToken = async () => {
    return await AsyncStorage.getItem('authToken');
  };

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputText.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const token = await getAuthToken();
      if (!token) {
        router.replace('/auth/login');
        return;
      }

      const response = await fetch(`${BACKEND_URL}/api/ai/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputText.trim(),
          history: messages,
          ageBand: user?.ageDefault || '60_72',
          planType: 'daily',
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          router.replace('/auth/login');
          return;
        }
        throw new Error('AI yanıt verirken hata oluştu');
      }

      const aiResponse: AIResponse = await response.json();
      setCurrentResponse(aiResponse);

      let responseText = '';
      
      if (aiResponse.finalize) {
        responseText = 'Harika! Planınız hazır. Size bir önizleme göstereyim:\n\n';
        
        if (aiResponse.domainOutcomes && aiResponse.domainOutcomes.length > 0) {
          responseText += '📋 **Hedeflenen Alanlar:**\n';
          aiResponse.domainOutcomes.forEach(outcome => {
            responseText += `• ${outcome.code}\n`;
          });
          responseText += '\n';
        }

        if (aiResponse.blocks?.activities && aiResponse.blocks.activities.length > 0) {
          responseText += '🎯 **Etkinlikler:**\n';
          aiResponse.blocks.activities.forEach((activity: any, index: number) => {
            responseText += `${index + 1}. ${activity.title}\n`;
          });
          responseText += '\n';
        }

        responseText += 'Planı kaydetmek ve PDF olarak indirmek ister misiniz?';
      } else {
        responseText = 'Planınızı tamamlamak için birkaç ek bilgiye ihtiyacım var:\n\n';
        
        if (aiResponse.followUpQuestions && aiResponse.followUpQuestions.length > 0) {
          aiResponse.followUpQuestions.forEach((question, index) => {
            responseText += `${index + 1}. ${question}\n`;
          });
        }
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: responseText,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      Alert.alert('Hata', 'Mesaj gönderilirken hata oluştu. Lütfen tekrar deneyin.');
      
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const savePlan = async () => {
    if (!currentResponse || !currentResponse.finalize) return;

    setIsLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) {
        router.replace('/auth/login');
        return;
      }

      // Prepare plan data with proper defaults and validation
      const planData = {
        date: currentResponse.date || new Date().toISOString().split('T')[0],
        ageBand: currentResponse.ageBand || user?.ageDefault || '60_72',
        planJson: currentResponse,
        title: `Günlük Plan - ${currentResponse.date || new Date().toLocaleDateString('tr-TR')}`,
      };

      console.log('Saving plan data:', planData);

      const response = await fetch(`${BACKEND_URL}/api/plans/daily`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(planData),
      });

      const responseData = await response.json();
      console.log('Plan save response:', response.status, responseData);

      if (response.ok) {
        Alert.alert('Başarılı', 'Plan kaydedildi!', [
          {
            text: 'Planları Görüntüle',
            onPress: () => router.push('/(tabs)/plans'),
          },
          {
            text: 'Yeni Plan',
            onPress: () => {
              setMessages([{
                role: 'assistant',
                content: 'Yeni bir plan oluşturmak için ne yapmak istiyorsunuz?',
                timestamp: new Date().toISOString(),
              }]);
              setCurrentResponse(null);
            },
          },
        ]);
      } else {
        console.error('Save failed:', responseData);
        Alert.alert('Hata', `Plan kaydedilemedi: ${responseData.detail || 'Bilinmeyen hata'}`);
      }
    } catch (error) {
      console.error('Save plan error:', error);
      Alert.alert('Hata', 'Plan kaydedilirken hata oluştu. Lütfen tekrar deneyin.');
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    Alert.alert(
      'Sohbeti Temizle',
      'Tüm sohbet geçmişi silinecek. Emin misiniz?',
      [
        { text: 'İptal', style: 'cancel' },
        {
          text: 'Temizle',
          style: 'destructive',
          onPress: () => {
            setMessages([{
              role: 'assistant',
              content: 'Merhaba! Ben MaarifPlanner AI asistanınızım. Günlük veya aylık plan oluşturmanızda size yardımcı olacağım. Hangi yaş bandı için plan oluşturmak istiyorsunuz ve ne tür etkinlikler planlıyorsunuz?',
              timestamp: new Date().toISOString(),
            }]);
            setCurrentResponse(null);
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Plan Asistanı</Text>
        <TouchableOpacity onPress={clearChat} style={styles.clearButton}>
          <Ionicons name="refresh-outline" size={24} color="#3498db" />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.chatContainer}
      >
        <ScrollView 
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((message, index) => (
            <View key={index} style={[
              styles.messageContainer,
              message.role === 'user' ? styles.userMessage : styles.assistantMessage
            ]}>
              <Text style={[
                styles.messageText,
                message.role === 'user' ? styles.userMessageText : styles.assistantMessageText
              ]}>
                {message.content}
              </Text>
              <Text style={styles.messageTime}>
                {new Date(message.timestamp).toLocaleTimeString('tr-TR', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </Text>
            </View>
          ))}
          
          {isLoading && (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="small" color="#3498db" />
              <Text style={styles.loadingText}>AI yanıt hazırlıyor...</Text>
            </View>
          )}
        </ScrollView>

        {currentResponse?.finalize && (
          <View style={styles.actionContainer}>
            <TouchableOpacity 
              style={styles.previewButton}
              onPress={() => setShowPreview(true)}
            >
              <Ionicons name="eye-outline" size={20} color="#3498db" />
              <Text style={styles.previewButtonText}>Önizleme</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.saveButton}
              onPress={savePlan}
              disabled={isLoading}
            >
              <Ionicons name="save-outline" size={20} color="white" />
              <Text style={styles.saveButtonText}>Planı Kaydet</Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            value={inputText}
            onChangeText={setInputText}
            placeholder="Mesajınızı yazın..."
            multiline
            maxLength={1000}
            onSubmitEditing={sendMessage}
          />
          <TouchableOpacity 
            style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.disabledButton]}
            onPress={sendMessage}
            disabled={!inputText.trim() || isLoading}
          >
            <Ionicons name="send" size={20} color="white" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Plan Preview Modal */}
      <Modal
        visible={showPreview}
        animationType="slide"
        presentationStyle="pageSheet"
      >
        <SafeAreaView style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={() => setShowPreview(false)}>
              <Ionicons name="close" size={24} color="#3498db" />
            </TouchableOpacity>
            <Text style={styles.modalTitle}>Plan Önizleme</Text>
            <TouchableOpacity onPress={savePlan} disabled={isLoading}>
              <Text style={styles.modalSaveText}>Kaydet</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalContent}>
            {currentResponse && (
              <View>
                <View style={styles.previewSection}>
                  <Text style={styles.previewSectionTitle}>Plan Bilgileri</Text>
                  <Text style={styles.previewItem}>📅 Tarih: {currentResponse.date || 'Bugün'}</Text>
                  <Text style={styles.previewItem}>👶 Yaş Bandı: {currentResponse.ageBand || '60-72 Ay'}</Text>
                  <Text style={styles.previewItem}>📝 Tür: {currentResponse.type === 'daily' ? 'Günlük Plan' : 'Aylık Plan'}</Text>
                </View>

                {currentResponse.domainOutcomes && currentResponse.domainOutcomes.length > 0 && (
                  <View style={styles.previewSection}>
                    <Text style={styles.previewSectionTitle}>Hedeflenen Alanlar</Text>
                    {currentResponse.domainOutcomes.map((outcome: any, index: number) => (
                      <View key={index} style={styles.outcomeContainer}>
                        <Text style={styles.outcomeCode}>• {outcome.code}</Text>
                        {outcome.indicators && outcome.indicators.length > 0 && (
                          <View style={styles.indicatorsContainer}>
                            {outcome.indicators.map((indicator: string, idx: number) => (
                              <Text key={idx} style={styles.indicator}>  - {indicator}</Text>
                            ))}
                          </View>
                        )}
                      </View>
                    ))}
                  </View>
                )}

                {currentResponse.blocks?.startOfDay && (
                  <View style={styles.previewSection}>
                    <Text style={styles.previewSectionTitle}>Güne Başlama</Text>
                    <Text style={styles.previewText}>{currentResponse.blocks.startOfDay}</Text>
                  </View>
                )}

                {currentResponse.blocks?.activities && currentResponse.blocks.activities.length > 0 && (
                  <View style={styles.previewSection}>
                    <Text style={styles.previewSectionTitle}>Etkinlikler</Text>
                    {currentResponse.blocks.activities.map((activity: any, index: number) => (
                      <View key={index} style={styles.activityContainer}>
                        <Text style={styles.activityTitle}>{index + 1}. {activity.title}</Text>
                        {activity.materials && activity.materials.length > 0 && (
                          <View>
                            <Text style={styles.activitySubtitle}>Materyaller:</Text>
                            {activity.materials.map((material: string, idx: number) => (
                              <Text key={idx} style={styles.activityItem}>• {material}</Text>
                            ))}
                          </View>
                        )}
                        {activity.steps && activity.steps.length > 0 && (
                          <View>
                            <Text style={styles.activitySubtitle}>Adımlar:</Text>
                            {activity.steps.map((step: string, idx: number) => (
                              <Text key={idx} style={styles.activityItem}>{idx + 1}. {step}</Text>
                            ))}
                          </View>
                        )}
                      </View>
                    ))}
                  </View>
                )}

                {currentResponse.blocks?.assessment && currentResponse.blocks.assessment.length > 0 && (
                  <View style={styles.previewSection}>
                    <Text style={styles.previewSectionTitle}>Değerlendirme</Text>
                    {currentResponse.blocks.assessment.map((item: string, index: number) => (
                      <Text key={index} style={styles.previewItem}>• {item}</Text>
                    ))}
                  </View>
                )}

                {currentResponse.notes && (
                  <View style={styles.previewSection}>
                    <Text style={styles.previewSectionTitle}>Notlar</Text>
                    <Text style={styles.previewText}>{currentResponse.notes}</Text>
                  </View>
                )}
              </View>
            )}
          </ScrollView>
        </SafeAreaView>
      </Modal>
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
  clearButton: {
    padding: 4,
  },
  chatContainer: {
    flex: 1,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    padding: 16,
    paddingBottom: 8,
  },
  messageContainer: {
    marginBottom: 16,
    maxWidth: '80%',
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#3498db',
    borderRadius: 16,
    padding: 12,
  },
  assistantMessage: {
    alignSelf: 'flex-start',
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e1e8ed',
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userMessageText: {
    color: 'white',
  },
  assistantMessageText: {
    color: '#2c3e50',
  },
  messageTime: {
    fontSize: 12,
    color: '#7f8c8d',
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e1e8ed',
    marginBottom: 16,
  },
  loadingText: {
    marginLeft: 8,
    color: '#7f8c8d',
    fontSize: 14,
  },
  actionContainer: {
    padding: 16,
    paddingTop: 8,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e1e8ed',
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#27ae60',
    borderRadius: 8,
    padding: 12,
  },
  saveButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e1e8ed',
    alignItems: 'flex-end',
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#e1e8ed',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    maxHeight: 100,
    marginRight: 8,
  },
  sendButton: {
    backgroundColor: '#3498db',
    borderRadius: 20,
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledButton: {
    backgroundColor: '#bdc3c7',
  },
});