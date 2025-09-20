import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import Constants from 'expo-constants';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || 'https://d7ae705b-7e8b-4812-a515-fa717748a941.preview.emergentagent.com';

interface SearchResult {
  id: string;
  title: string;
  content: string;
  type: string;
  relevance: number;
}

export default function MatrixScreen() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  useEffect(() => {
    loadRecentSearches();
  }, []);

  const loadRecentSearches = async () => {
    try {
      const stored = await AsyncStorage.getItem('recentMatrixSearches');
      if (stored) {
        setRecentSearches(JSON.parse(stored));
      }
    } catch (error) {
      console.error('Error loading recent searches:', error);
    }
  };

  const saveRecentSearch = async (query: string) => {
    try {
      const updated = [query, ...recentSearches.filter(s => s !== query)].slice(0, 5);
      setRecentSearches(updated);
      await AsyncStorage.setItem('recentMatrixSearches', JSON.stringify(updated));
    } catch (error) {
      console.error('Error saving recent search:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      Alert.alert('Uyarı', 'Lütfen arama terimi girin');
      return;
    }

    setIsLoading(true);
    try {
      const token = await AsyncStorage.getItem('authToken');
      if (!token) {
        Alert.alert('Hata', 'Oturum süresi dolmuş. Lütfen tekrar giriş yapın.');
        router.replace('/auth/login');
        return;
      }

      saveRecentSearch(searchQuery.trim());

      const response = await fetch(`${BACKEND_URL}/api/matrix/search`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery.trim(),
          limit: 20,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.results || []);
      } else if (response.status === 401) {
        Alert.alert('Hata', 'Oturum süresi dolmuş. Lütfen tekrar giriş yapın.');
        router.replace('/auth/login');
      } else {
        const errorData = await response.json();
        Alert.alert('Hata', errorData.detail || 'Arama sırasında bir hata oluştu');
      }
    } catch (error) {
      console.error('Search error:', error);
      Alert.alert('Hata', 'Bağlantı hatası. Lütfen tekrar deneyin.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRecentSearch = (query: string) => {
    setSearchQuery(query);
  };

  const clearRecentSearches = async () => {
    try {
      setRecentSearches([]);
      await AsyncStorage.removeItem('recentMatrixSearches');
    } catch (error) {
      console.error('Error clearing recent searches:', error);
    }
  };

  const renderSearchResult = (result: SearchResult) => (
    <View key={result.id} style={styles.resultCard}>
      <View style={styles.resultHeader}>
        <Text style={styles.resultTitle}>{result.title}</Text>
        <View style={styles.relevanceContainer}>
          <Text style={styles.relevanceText}>{Math.round(result.relevance * 100)}%</Text>
        </View>
      </View>
      <Text style={styles.resultContent} numberOfLines={3}>
        {result.content}
      </Text>
      <View style={styles.resultFooter}>
        <Text style={styles.resultType}>{result.type}</Text>
        <TouchableOpacity style={styles.viewButton}>
          <Text style={styles.viewButtonText}>Görüntüle</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🔍 Matrix Arama</Text>
        <Text style={styles.subtitle}>Eğitim içeriklerini keşfedin</Text>
      </View>

      <View style={styles.searchContainer}>
        <View style={styles.searchInputContainer}>
          <Ionicons name="search" size={20} color="#7f8c8d" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            placeholder="Arama terimini girin..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            onSubmitEditing={handleSearch}
            returnKeyType="search"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')} style={styles.clearButton}>
              <Ionicons name="close-circle" size={20} color="#7f8c8d" />
            </TouchableOpacity>
          )}
        </View>
        
        <TouchableOpacity 
          style={[styles.searchButton, isLoading && styles.disabledButton]}
          onPress={handleSearch}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Ionicons name="search" size={20} color="#fff" />
          )}
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {recentSearches.length > 0 && searchResults.length === 0 && (
          <View style={styles.recentContainer}>
            <View style={styles.recentHeader}>
              <Text style={styles.recentTitle}>Son Aramalar</Text>
              <TouchableOpacity onPress={clearRecentSearches}>
                <Text style={styles.clearText}>Temizle</Text>
              </TouchableOpacity>
            </View>
            {recentSearches.map((query, index) => (
              <TouchableOpacity
                key={index}
                style={styles.recentItem}
                onPress={() => handleRecentSearch(query)}
              >
                <Ionicons name="time-outline" size={16} color="#7f8c8d" />
                <Text style={styles.recentQuery}>{query}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {searchResults.length > 0 && (
          <View style={styles.resultsContainer}>
            <Text style={styles.resultsTitle}>
              {searchResults.length} sonuç bulundu
            </Text>
            {searchResults.map(renderSearchResult)}
          </View>
        )}

        {searchResults.length === 0 && searchQuery && !isLoading && (
          <View style={styles.noResultsContainer}>
            <Ionicons name="search-outline" size={64} color="#bdc3c7" />
            <Text style={styles.noResultsText}>Sonuç bulunamadı</Text>
            <Text style={styles.noResultsSubtext}>
              Farklı anahtar kelimeler deneyiniz veya arama terimini değiştiriniz
            </Text>
          </View>
        )}

        {searchResults.length === 0 && !searchQuery && (
          <View style={styles.emptyContainer}>
            <Ionicons name="library-outline" size={64} color="#bdc3c7" />
            <Text style={styles.emptyText}>Matrix Arama</Text>
            <Text style={styles.emptySubtext}>
              Eğitim programı, etkinlikler ve kaynaklarda arama yapın
            </Text>
            <View style={styles.suggestionsContainer}>
              <Text style={styles.suggestionsTitle}>Örnek Aramalar:</Text>
              {['Matematik etkinlikleri', 'Sanat çalışmaları', 'Okuma yazma', 'Oyun örnekleri'].map((suggestion, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.suggestionChip}
                  onPress={() => handleRecentSearch(suggestion)}
                >
                  <Text style={styles.suggestionText}>{suggestion}</Text>
                </TouchableOpacity>
              ))}
            </View>
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
  searchContainer: {
    flexDirection: 'row',
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e1e8ed',
  },
  searchInputContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f1f2f6',
    borderRadius: 10,
    paddingHorizontal: 15,
    marginRight: 10,
  },
  searchIcon: {
    marginRight: 10,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 12,
    fontSize: 16,
    color: '#2c3e50',
  },
  clearButton: {
    padding: 5,
  },
  searchButton: {
    backgroundColor: '#3498db',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledButton: {
    backgroundColor: '#95a5a6',
  },
  content: {
    flex: 1,
  },
  recentContainer: {
    padding: 20,
    backgroundColor: '#fff',
    marginBottom: 10,
  },
  recentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  recentTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2c3e50',
  },
  clearText: {
    color: '#e74c3c',
    fontSize: 14,
  },
  recentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#ecf0f1',
  },
  recentQuery: {
    marginLeft: 10,
    fontSize: 16,
    color: '#2c3e50',
  },
  resultsContainer: {
    padding: 20,
  },
  resultsTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 15,
  },
  resultCard: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    flex: 1,
    marginRight: 10,
  },
  relevanceContainer: {
    backgroundColor: '#3498db',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  relevanceText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  resultContent: {
    fontSize: 14,
    color: '#7f8c8d',
    lineHeight: 20,
    marginBottom: 10,
  },
  resultFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  resultType: {
    fontSize: 12,
    color: '#95a5a6',
    backgroundColor: '#ecf0f1',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  viewButton: {
    backgroundColor: '#27ae60',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 6,
  },
  viewButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  noResultsContainer: {
    padding: 40,
    alignItems: 'center',
  },
  noResultsText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#7f8c8d',
    marginTop: 20,
    marginBottom: 10,
  },
  noResultsSubtext: {
    fontSize: 14,
    color: '#95a5a6',
    textAlign: 'center',
    lineHeight: 20,
  },
  emptyContainer: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#7f8c8d',
    marginTop: 20,
    marginBottom: 10,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#95a5a6',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 30,
  },
  suggestionsContainer: {
    alignItems: 'center',
  },
  suggestionsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 15,
  },
  suggestionChip: {
    backgroundColor: '#3498db',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 20,
    marginBottom: 10,
  },
  suggestionText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
  },
});